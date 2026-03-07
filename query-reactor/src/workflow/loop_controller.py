"""Loop management and control flow for QueryReactor workflow."""

from typing import Dict, Any, Optional
from ..models import ReactorState, SMRDecision
from ..models.state import StateManager
import logging

logger = logging.getLogger(__name__)


class LoopController:
    """Manages loop control flow and prevents infinite cycles."""
    
    def __init__(self):
        self.logger = logger
    
    def should_loop_to_preprocessor_from_smr(self, state: ReactorState) -> bool:
        """Determine if SMR should loop back to query preprocessor."""
        
        # Check SMR decision
        smr_decision = getattr(state, 'smr_decision', None)
        if smr_decision != SMRDecision.needs_better_decomposition.value:
            return False
        
        # Check loop limits
        current_count = state.loop_counters.smartretrieval_to_qp
        max_count = state.loop_limits.get("loop.max.smartretrieval_to_qp", 2)
        
        if current_count >= max_count:
            self.logger.warning(f"SMR->QP loop limit reached ({current_count}/{max_count})")
            return False
        
        return True
    
    def should_loop_to_answer_creator_from_check(self, state: ReactorState) -> bool:
        """Determine if answer check should loop back to answer creator."""
        
        # Check verification result
        verification_result = getattr(state, 'verification_result', None)
        if not verification_result or verification_result.is_valid:
            return False
        
        # Check if regeneration is suggested
        if not verification_result.suggestions:
            return False
        
        regeneration_suggested = any(
            'regenerate' in suggestion.lower() 
            for suggestion in verification_result.suggestions
        )
        
        if not regeneration_suggested:
            return False
        
        # Check loop limits
        current_count = state.loop_counters.answercheck_to_ac
        max_count = state.loop_limits.get("loop.max.answercheck_to_ac", 3)
        
        if current_count >= max_count:
            self.logger.warning(f"ACK->AC loop limit reached ({current_count}/{max_count})")
            return False
        
        return True
    
    def should_loop_to_preprocessor_from_check(self, state: ReactorState) -> bool:
        """Determine if answer check should loop back to query preprocessor."""
        
        # Check verification result
        verification_result = getattr(state, 'verification_result', None)
        if not verification_result or verification_result.is_valid:
            return False
        
        # Check if query refinement is suggested
        if not verification_result.issues:
            return False
        
        query_refinement_needed = any(
            any(indicator in issue.lower() for indicator in [
                'does not adequately address',
                'does not match the type of question',
                'insufficient evidence'
            ])
            for issue in verification_result.issues
        )
        
        if not query_refinement_needed:
            return False
        
        # Check loop limits
        current_count = state.loop_counters.answercheck_to_qp
        max_count = state.loop_limits.get("loop.max.answercheck_to_qp", 1)
        
        if current_count >= max_count:
            self.logger.warning(f"ACK->QP loop limit reached ({current_count}/{max_count})")
            return False
        
        return True
    
    def increment_loop_counter(self, state: ReactorState, loop_type: str) -> int:
        """Increment loop counter and return new value."""
        new_count = state.increment_loop_counter(loop_type)
        self.logger.info(f"Loop counter incremented: {loop_type} = {new_count}")
        return new_count
    
    def get_loop_status(self, state: ReactorState) -> Dict[str, Any]:
        """Get current loop status for debugging."""
        return {
            "counters": {
                "smartretrieval_to_qp": state.loop_counters.smartretrieval_to_qp,
                "answercheck_to_ac": state.loop_counters.answercheck_to_ac,
                "answercheck_to_qp": state.loop_counters.answercheck_to_qp
            },
            "limits": state.loop_limits,
            "can_loop": {
                "smr_to_qp": not state.check_loop_limit("smartretrieval_to_qp"),
                "ack_to_ac": not state.check_loop_limit("answercheck_to_ac"),
                "ack_to_qp": not state.check_loop_limit("answercheck_to_qp")
            }
        }
    
    def force_termination(self, state: ReactorState, reason: str) -> None:
        """Force workflow termination due to loop limits."""
        self.logger.warning(f"Forcing workflow termination: {reason}")
        
        # Set state to force termination
        state.smr_decision = SMRDecision.insufficient_evidence.value
        state.smr_reasoning = f"Terminated due to loop limits: {reason}"
        
        # Clear any loop feedback
        state.clear_loop_feedback()
    
    def prepare_loop_feedback(self, state: ReactorState, loop_type: str, 
                            feedback: str) -> None:
        """Prepare feedback for loop iteration."""
        
        # Set loop feedback in state
        state.set_loop_feedback(feedback)
        
        # Log the loop iteration
        self.logger.info(f"Preparing loop iteration ({loop_type}): {feedback[:100]}...")
    
    def clear_loop_state(self, state: ReactorState) -> None:
        """Clear loop-related state for fresh processing."""
        state.clear_loop_feedback()
        
        # Reset certain state flags that might interfere with loops
        if hasattr(state, 'smr_decision'):
            delattr(state, 'smr_decision')
        if hasattr(state, 'verification_result'):
            delattr(state, 'verification_result')


# Global loop controller instance
loop_controller = LoopController()