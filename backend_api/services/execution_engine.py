from sqlalchemy.orm import Session
from typing import Dict, Optional, List

from entities.application import Application, VerificationAttempt, VerificationDecision, FinalDecision, ApplicationStatus
from entities.verification_profile import ProfileVersion, VerificationStep, VerificationEdge, EdgeCondition
from services.webhook_dispatcher import WebhookDispatcher
from entities.webhook import WebhookEventType

class ExecutionEngine:
    """
    The ExecutionEngine is responsible for orchestrating the verification flow
    defined by a ProfileVersion for a specific Application.
    It separates the "What should happen" (Flow Builder definition) from 
    the "How it happens" (Execution).
    """

    def __init__(self, db: Session, application_id: int):
        self.db = db
        self.application = db.query(Application).filter(Application.id == application_id).first()
        if not self.application:
            raise ValueError(f"Application {application_id} not found")
            
        self.version = db.query(ProfileVersion).filter(ProfileVersion.id == self.application.profile_version_id).first()
        if not self.version:
            raise ValueError(f"ProfileVersion {self.application.profile_version_id} not found")

        # Pre-load graph into memory for easy traversal
        self.nodes_by_key = {step.node_key: step for step in self.version.steps}
        self.edges = self.version.edges
        
    def _evaluate_condition(self, condition: dict, context: dict) -> bool:
        if not condition:
            return True # No condition implies unconditional traversal
            
        # Support legacy enum string if some edges still have it during migration
        if isinstance(condition, str):
            # Try to map simple SUCCESS/FAILURE string to status field
            return True # Fallback for now

        try:
            import json_logic
            return bool(json_logic.apply(condition, context))
        except ImportError:
            # Fallback if json-logic-py is not installed yet
            return True

    def _get_next_steps(self, current_node_key: str, context: dict) -> List[VerificationStep]:
        """
        Given a current node and the accumulated context,
        evaluate edges and return the next steps to execute.
        """
        next_steps = []
        for edge in self.edges:
            if edge.source_step_key == current_node_key:
                if self._evaluate_condition(edge.condition, context):
                    if edge.target_step_key in self.nodes_by_key:
                        next_steps.append(self.nodes_by_key[edge.target_step_key])
        return next_steps

    def start_execution(self):
        """
        Initiates the execution of the application's verification flow.
        For V1, this foundation will simply identify the root nodes (nodes with no incoming edges)
        and prepare the first VerificationAttempts.
        """
        # Find root nodes (no incoming edges)
        target_keys = {edge.target_step_key for edge in self.edges}
        root_nodes = [step for step in self.version.steps if step.node_key not in target_keys]

        if not root_nodes:
            raise ValueError("Invalid flow graph: No starting node found.")
            
        # In a real execution, we would create VerificationAttempt records for root nodes
        # and perhaps place them on a task queue to be executed by service adapters.
        
        self.application.status = ApplicationStatus.REVIEW
        self.db.commit()
        self.db.refresh(self.application)

        # Trigger webhook
        WebhookDispatcher.trigger_event(
            company_id=self.application.company_id,
            application_id=self.application.id,
            event_type=WebhookEventType.VERIFICATION_STARTED,
            payload={
                "application_id": self.application.id, 
                "profile_version_id": self.version.id, 
                "status": self.application.status.value
            }
        )
        
        return [node.node_key for node in root_nodes]

    def record_step_completion(self, step_key: str, status, result_data: dict = None):
        """
        Records the completion of a VerificationAttempt.
        Builds the context from all previous attempts and evaluates the next steps.
        """
        attempt = self.db.query(VerificationAttempt).filter(
            VerificationAttempt.application_id == self.application.id,
            VerificationAttempt.step_key == step_key,
            VerificationAttempt.status == "PENDING"  # Assuming string or enum
        ).first()
        
        if attempt:
            attempt.status = status
            attempt.result_data = result_data
            from datetime import datetime
            attempt.completed_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(attempt)
            
            # Trigger webhook for step completion
            WebhookDispatcher.trigger_event(
                company_id=self.application.company_id,
                application_id=self.application.id,
                event_type=WebhookEventType.VERIFICATION_STEP_COMPLETED,
                payload={
                    "application_id": self.application.id, 
                    "step_key": step_key,
                    "status": status.value if hasattr(status, 'value') else status,
                    "result_data": result_data
                }
            )

        # Build context from all completed attempts
        context = {}
        all_attempts = self.db.query(VerificationAttempt).filter(
            VerificationAttempt.application_id == self.application.id
        ).all()
        for a in all_attempts:
            # We assume result_data is a dict containing metrics e.g. {"confidence": 0.85}
            # We map this into context[step_key] = result_data
            context[a.step_key] = a.result_data or {}
            context[a.step_key]["status"] = a.status.value if hasattr(a.status, 'value') else a.status
            
        next_steps = self._get_next_steps(step_key, context)
        return [step.node_key for step in next_steps]

    def finalize_decision(self, final_decision: FinalDecision, reason: str = None, score: float = None):
        """
        Record the final VerificationDecision for the application.
        """
        decision = VerificationDecision(
            company_id=self.application.company_id,
            application_id=self.application.id,
            decision=final_decision,
            reason=reason,
            confidence_score=score
        )
        self.db.add(decision)
        
        # Update Application status
        if final_decision == FinalDecision.APPROVED:
            self.application.status = ApplicationStatus.APPROVED
        elif final_decision == FinalDecision.REJECTED:
            self.application.status = ApplicationStatus.REJECTED
        elif final_decision == FinalDecision.HUMAN_REVIEW:
            self.application.status = ApplicationStatus.REVIEW
        elif final_decision == FinalDecision.FAILED:
            self.application.status = ApplicationStatus.FAILED
            
        self.db.commit()
        
        # Trigger webhook for final decision
        event = WebhookEventType.VERIFICATION_APPROVED if final_decision == FinalDecision.APPROVED else WebhookEventType.VERIFICATION_REJECTED
        if final_decision == FinalDecision.HUMAN_REVIEW:
            event = WebhookEventType.VERIFICATION_REVIEW_REQUIRED
            
        WebhookDispatcher.trigger_event(
            company_id=self.application.company_id,
            application_id=self.application.id,
            event_type=event,
            payload={
                "application_id": self.application.id, 
                "decision": final_decision.value,
                "reason": reason
            }
        )
        
        return decision
