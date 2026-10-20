class BenchmarkConditioningBarrier:
    """Pass conditioning through while waiting on optional conditioning inputs."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {"conditioning": ("CONDITIONING",)},
            "optional": {
                f"ready_{index}": ("CONDITIONING",)
                for index in range(1, 13)
            },
        }

    RETURN_TYPES = ("CONDITIONING",)
    RETURN_NAMES = ("conditioning",)
    FUNCTION = "pass_through"
    CATEGORY = "feature benchmark"

    def pass_through(self, conditioning, **_ready):
        return (conditioning,)


NODE_CLASS_MAPPINGS = {
    "BenchmarkConditioningBarrier": BenchmarkConditioningBarrier,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "BenchmarkConditioningBarrier": "Benchmark Conditioning Barrier",
}
