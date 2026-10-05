"""Model managers; loading camera settings must not import TensorFlow."""
__all__ = ["GazeCorrector"]


def __getattr__(name):
    if name == "GazeCorrector":
        from model_managers.gaze_corrector_v1 import GazeCorrector
        return GazeCorrector
    raise AttributeError(name)
