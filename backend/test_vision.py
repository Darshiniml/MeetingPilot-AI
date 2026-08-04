"""Standalone local smoke test for the Meeting Vision Engine foundation."""

from app.vision import get_vision_service


def main() -> None:
    try:
        result = get_vision_service().inspect_once()
    except RuntimeError as error:
        print(f"Vision capture unavailable: {error}")
        return
    if result.meeting_window is None:
        print("Platform: No supported meeting window detected")
        print("Participants Found: 0")
        return
    window = result.meeting_window.bounding_box
    print(f"Platform: {result.meeting_window.platform_name}")
    print(f"Window: x={window.x}, y={window.y}, width={window.width}, height={window.height}")
    print(f"Participants Found: {len(result.participants)}")
    for participant in result.participants:
        box = participant.bounding_box
        print(f"{participant.id}: x={box.x}, y={box.y}, width={box.width}, height={box.height}")


if __name__ == "__main__":
    main()
