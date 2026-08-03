package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"doctor-service/auth/jwt"
	"doctor-service/auth/token"
	"doctor-service/config"
	"doctor-service/controllers"
	"doctor-service/entities"
	"doctor-service/events"
	"doctor-service/notifications"
	"doctor-service/observability"
	"doctor-service/ocr"
	"doctor-service/prescriptions"
	"doctor-service/repositories"
	"doctor-service/security"
	"doctor-service/services"
	"doctor-service/sms"
	"doctor-service/storage"
	"doctor-service/storage/providers/local"
	"doctor-service/verification/comparison"
	"doctor-service/verification/council"
	"doctor-service/verification/decision"
	"doctor-service/verification/fraud"
	"doctor-service/worker"

	"github.com/glebarez/sqlite"
	"gorm.io/driver/postgres"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"
)

func main() {
	log.Println("=======================================================")
	log.Println("Starting Enterprise Doctor Verification Service v1.0.0")
	log.Println("=======================================================")

	// Load Configuration
	appCfg := config.LoadConfig()

	// 1. Setup DB Connection (PostgreSQL with Pure-Go SQLite fallback)
	dbHost := getEnv("DB_HOST", "localhost")
	dbPort := getEnv("DB_PORT", "5432")
	dbUser := getEnv("DB_USER", "postgres")
	dbPass := getEnv("DB_PASSWORD", "secretpassword")
	dbName := getEnv("DB_NAME", "doctor_verification_db")

	dsn := fmt.Sprintf("host=%s user=%s password=%s dbname=%s port=%s sslmode=disable",
		dbHost, dbUser, dbPass, dbName, dbPort)

	customLogger := logger.New(
		log.New(os.Stdout, "\r\n", log.LstdFlags),
		logger.Config{
			SlowThreshold:             200 * time.Millisecond,
			LogLevel:                  logger.Error,
			IgnoreRecordNotFoundError: true,
			Colorful:                  true,
		},
	)

	gormConfig := &gorm.Config{
		Logger: customLogger,
	}

	// Try PostgreSQL connection silently
	silentConfig := &gorm.Config{Logger: logger.Discard}
	db, err := gorm.Open(postgres.Open(dsn), silentConfig)
	if err != nil {
		log.Printf("[DB NOTICE] PostgreSQL not available on %s:%s. Falling back to local embedded database (SQLite: ./doctor_verification.db)...", dbHost, dbPort)

		db, err = gorm.Open(sqlite.Open("./doctor_verification.db"), gormConfig)
		if err != nil {
			log.Fatalf("[DB FATAL] Failed to initialize database: %v", err)
		}
		log.Println("[DB] Successfully initialized local embedded database (SQLite: ./doctor_verification.db).")
	} else {
		db.Logger = customLogger
		log.Println("[DB] Successfully connected to PostgreSQL database.")
	}

	// Auto Migrate database schema
	log.Println("[DB] Running schema auto-migrations...")
	err = db.AutoMigrate(
		&entities.Doctor{},
		&entities.DoctorLicense{},
		&entities.DoctorQualification{},
		&entities.DoctorClinic{},
		&entities.DoctorDocument{},
		&entities.VerificationHistory{},
		&entities.AdminUser{},
		&entities.OTPVerification{},
		&entities.RefreshToken{},
		&entities.VerificationJob{},
		&entities.DocumentOCRResult{},
		&entities.AdminAction{},
		&entities.DoctorNote{},
		&entities.VerificationFlag{},
		&entities.AuditEvent{},
		&entities.VerificationDeadJob{},
		&entities.Prescription{},
	)
	if err != nil {
		log.Printf("[DB WARNING] Auto migration notice: %v", err)
	} else {
		log.Println("[DB] Schema auto-migrations completed successfully.")
	}

	// 2. Initialize Core Components
	jwtSecret := getEnv("JWT_SECRET", "super-secret-jwt-key-2026")
	jwtMgr := jwt.NewJWTManager(jwtSecret, 15*time.Minute)
	refreshTokenMgr := token.NewRefreshTokenManager(appCfg.RefreshTokenDuration)
	smsProv := sms.NewMockSMSProvider()
	storageProv, _ := local.NewLocalStorageProvider("./uploads", "http://localhost:8080/uploads")
	fileValidator := storage.NewFileValidator(10*1024*1024, 300)
	virusScanner := storage.NewDefaultVirusScanner()
	ocrProv := ocr.NewMockOCRProvider()
	councilProv := council.NewNMCRegistryAdapter()
	notificationProv := notifications.NewMockNotificationProvider()
	eventBus := events.NewMemoryEventBus()
	featureFlags := config.GetFeatureFlags()

	_ = featureFlags

	// Repositories
	doctorRepo := repositories.NewDoctorRepository(db)
	otpRepo := repositories.NewOTPRepository(db)
	refreshRepo := repositories.NewRefreshTokenRepository(db)
	licenseRepo := repositories.NewLicenseRepository(db)
	qualRepo := repositories.NewQualificationRepository(db)
	clinicRepo := repositories.NewClinicRepository(db)
	docRepo := repositories.NewDocumentRepository(db)
	historyRepo := repositories.NewVerificationHistoryRepository(db)
	jobRepo := repositories.NewJobRepository(db)
	ocrRepo := repositories.NewOCRRepository(db)
	adminActionRepo := repositories.NewAdminActionRepository(db)
	noteRepo := repositories.NewNoteRepository(db)
	flagRepo := repositories.NewFlagRepository(db)
	dlqRepo := repositories.NewDLQRepository(db)
	auditRepo := repositories.NewAuditRepository(db)

	_ = auditRepo

	// Services & Verification Engines
	comparator := comparison.NewComparator()
	fraudDetector := fraud.NewFraudDetector()
	decisionEngine := decision.NewDecisionEngine()

	pipelineService := services.NewVerificationPipelineService(
		jobRepo, doctorRepo, docRepo, licenseRepo, qualRepo, historyRepo,
		ocrRepo, ocrProv, comparator, councilProv, fraudDetector, decisionEngine,
	)

	authService := services.NewAuthService(doctorRepo, otpRepo, refreshRepo, smsProv, jwtMgr, refreshTokenMgr, appCfg)
	profileService := services.NewProfileService(doctorRepo)
	licenseService := services.NewLicenseService(licenseRepo)
	qualService := services.NewQualificationService(qualRepo)
	clinicService := services.NewClinicService(clinicRepo)
	docService := services.NewDocumentService(doctorRepo, docRepo, storageProv, fileValidator, virusScanner)
	submissionService := services.NewSubmissionService(doctorRepo, licenseRepo, qualRepo, clinicRepo, docRepo, historyRepo, jobRepo)
	adminReviewService := services.NewAdminReviewService(doctorRepo, licenseRepo, qualRepo, clinicRepo, docRepo, ocrRepo, historyRepo, adminActionRepo, noteRepo, flagRepo, notificationProv, comparator)
	analyticsService := services.NewAnalyticsService(db, doctorRepo, dlqRepo)

	// Controllers
	authCtrl := controllers.NewAuthController(authService)
	profileCtrl := controllers.NewProfileController(profileService)
	licenseCtrl := controllers.NewLicenseController(licenseService)
	qualCtrl := controllers.NewQualificationController(qualService)
	clinicCtrl := controllers.NewClinicController(clinicService)
	docCtrl := controllers.NewDocumentController(docService)
	submissionCtrl := controllers.NewSubmissionController(submissionService)
	adminCtrl := controllers.NewAdminController(adminReviewService)
	prescriptionCtrl := controllers.NewPrescriptionController()
	analyticsCtrl := controllers.NewAnalyticsController(analyticsService)
	dlqCtrl := controllers.NewDLQController(dlqRepo, jobRepo)
	healthCtrl := observability.NewHealthHandler(db)

	// Security & Rate Limiting
	rateLimiter := security.NewRateLimiter(60, 1*time.Minute)
	prescriptionGuard := security.NewPrescriptionAuthGuard(doctorRepo)

	// Background Worker
	bgWorker := worker.NewVerificationWorker(jobRepo, pipelineService, 2*time.Second)
	ctx, cancelWorker := context.WithCancel(context.Background())
	go bgWorker.Start(ctx)

	// 3. Register HTTP Routes
	mux := http.NewServeMux()

	// Observability & Metrics
	mux.HandleFunc("/health/live", healthCtrl.Live)
	mux.HandleFunc("/health/ready", healthCtrl.Ready)
	mux.Handle("/metrics", observability.GlobalMetrics)

	// Auth APIs
	mux.Handle("/api/v1/doctors/register", rateLimiter.Limit(http.HandlerFunc(authCtrl.Register)))
	mux.Handle("/api/v1/doctors/verify-otp", rateLimiter.Limit(http.HandlerFunc(authCtrl.VerifyOTP)))
	mux.Handle("/api/v1/doctors/login", rateLimiter.Limit(http.HandlerFunc(authCtrl.Login)))

	// Doctor Profile & Uploads
	mux.HandleFunc("/api/v1/doctors/profile", profileCtrl.HandleProfile)
	mux.HandleFunc("/api/v1/doctors/licenses", licenseCtrl.HandleLicenses)
	mux.HandleFunc("/api/v1/doctors/qualifications", qualCtrl.HandleQualifications)
	mux.HandleFunc("/api/v1/doctors/clinics", clinicCtrl.HandleClinics)
	mux.Handle("/api/v1/doctors/documents", rateLimiter.Limit(http.HandlerFunc(docCtrl.HandleDocuments)))
	mux.HandleFunc("/api/v1/doctors/submit-verification", submissionCtrl.SubmitVerification)

	// Admin Verification Portal APIs
	mux.HandleFunc("/api/v1/admin/verifications/detail", adminCtrl.GetDoctorVerificationDetail)
	mux.HandleFunc("/api/v1/admin/verifications/assign", adminCtrl.AssignDoctor)
	mux.HandleFunc("/api/v1/admin/verifications/approve", adminCtrl.ApproveDoctor)
	mux.HandleFunc("/api/v1/admin/verifications/reject", adminCtrl.RejectDoctor)
	mux.HandleFunc("/api/v1/admin/verifications/request-documents", adminCtrl.RequestDocuments)
	mux.HandleFunc("/api/v1/admin/verifications/notes", adminCtrl.AddNote)
	mux.HandleFunc("/api/v1/admin/search", analyticsCtrl.Search)
	mux.HandleFunc("/api/v1/admin/analytics", analyticsCtrl.GetAnalytics)

	// DLQ APIs
	mux.HandleFunc("/api/v1/admin/dead-jobs", dlqCtrl.ListDeadJobs)
	mux.HandleFunc("/api/v1/admin/dead-jobs/retry", dlqCtrl.RetryDeadJob)

	// Prescriptions API (Guarded)
	mux.Handle("/api/v1/prescriptions", prescriptionGuard.RequireVerifiedDoctorForPrescription(http.HandlerFunc(prescriptionCtrl.CreatePrescription)))

	// Serve Uploaded Files
	mux.Handle("/uploads/", http.StripPrefix("/uploads/", http.FileServer(http.Dir("./uploads"))))

	// Serve Web Portal Frontend
	mux.Handle("/", http.FileServer(http.Dir("./public")))

	// 4. Start HTTP Server (with automatic port fallback if 8080 is occupied)
	port := getEnv("PORT", "8080")
	server := &http.Server{
		Addr:         ":" + port,
		Handler:      mux,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 15 * time.Second,
	}

	go func() {
		log.Printf("Server listening and serving HTTP on port %s...", port)
		log.Printf("Ready to receive requests at http://localhost:%s/", port)
		err := server.ListenAndServe()
		if err != nil && err != http.ErrServerClosed {
			log.Printf("[SERVER NOTICE] Port %s bound or busy (%v). Trying fallback port 8081...", port, err)
			fallbackServer := &http.Server{
				Addr:         ":8081",
				Handler:      mux,
				ReadTimeout:  15 * time.Second,
				WriteTimeout: 15 * time.Second,
			}
			log.Printf("Server listening and serving HTTP on fallback port 8081...")
			log.Printf("Ready to receive requests at http://localhost:8081/")
			if err := fallbackServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
				log.Fatalf("HTTP server failed on fallback port: %v", err)
			}
		}
	}()

	// Graceful Shutdown Handler
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit
	log.Println("Shutting down Doctor Verification Service gracefully...")

	cancelWorker()
	ctxShutdown, cancelShutdown := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancelShutdown()

	if err := server.Shutdown(ctxShutdown); err != nil {
		log.Fatalf("Server forced to shutdown: %v", err)
	}

	log.Println("Server exited cleanly.")

	// Keep unused variables clean
	_ = eventBus
	_ = rsaGen()
}

func rsaGen() interface{} {
	gen, _ := prescriptions.NewRSAPrescriptionGenerator()
	return gen
}

func getEnv(key, fallback string) string {
	if val := os.Getenv(key); val != "" {
		return val
	}
	return fallback
}
