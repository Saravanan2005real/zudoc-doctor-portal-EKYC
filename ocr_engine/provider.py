from abc import ABC, abstractmethod

class ExtractedFields:
    def __init__(self, doctor_name="", registration_number="", registration_council="", registration_year=0, degree="", specialization="", university="", college="", year_completed=0, dob="", govt_id_number=""):
        self.doctor_name = doctor_name
        self.registration_number = registration_number
        self.registration_council = registration_council
        self.registration_year = registration_year
        self.degree = degree
        self.specialization = specialization
        self.university = university
        self.college = college
        self.year_completed = year_completed
        self.dob = dob
        self.govt_id_number = govt_id_number

class OCRResult:
    def __init__(self, raw_json, parsed_fields, confidence, processing_time_ms):
        self.raw_json = raw_json
        self.parsed_fields = parsed_fields
        self.confidence = confidence
        self.processing_time_ms = processing_time_ms

class OCRProvider(ABC):
    @abstractmethod
    def extract(self, context, doc, file_reader) -> OCRResult:
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        pass
