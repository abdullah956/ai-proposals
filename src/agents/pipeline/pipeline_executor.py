"""Pipeline executor for running pipelines with progress tracking."""

from typing import Any, Dict, Optional

from agents.pipeline.base_pipeline import BasePipeline


class PipelineExecutor:
    """Executes pipelines and tracks progress."""

    def __init__(self, pipeline: BasePipeline):
        """Initialize the pipeline executor.

        Args:
            pipeline: Pipeline instance to execute
        """
        self.pipeline = pipeline
        self.progress_callback = None

    def set_progress_callback(self, callback):
        """Set a callback function for progress updates.

        Args:
            callback: Function that receives (stage, message) updates
        """
        self.progress_callback = callback

    def _notify_progress(self, stage: str, message: str):
        """Notify progress update.

        Args:
            stage: Current stage name
            message: Progress message
        """
        if self.progress_callback:
            self.progress_callback(stage, message)
        else:
            print(f"[{stage}] {message}")

    def execute(self, state: Dict, streaming_callback: Optional[Any] = None) -> Dict:
        """Execute the pipeline.

        Args:
            state: Current proposal state
            streaming_callback: Optional callback for streaming updates

        Returns:
            Updated state dictionary
        """
        self._notify_progress("start", f"Starting {self.pipeline.display_name}...")

        try:
            # Validate prerequisites
            if not self.pipeline.validate_prerequisites(state):
                raise ValueError("Pipeline prerequisites not met")

            # Execute pipeline
            updated_state = self.pipeline.execute(state, streaming_callback=streaming_callback)

            self._notify_progress(
                "complete", f"{self.pipeline.display_name} completed successfully"
            )

            return updated_state

        except Exception as e:
            self._notify_progress("error", f"Pipeline execution failed: {str(e)}")
            raise
