# Docker-based Computer Use Example Tool
# Actions supported: click, double_click, scroll, type, wait, keypress, drag, move, screenshot

import time


def handle_computer_actions(vm, actions):
    button_map = {"left": 1, "middle": 2, "right": 3}

    for action in actions:
        match action.type:
            case "click":
                button = button_map.get(getattr(action, "button", "left"), 1)
                docker_exec(
                    f"DISPLAY={vm.display} xdotool mousemove {action.x} {action.y} click {button}",
                    vm.container_name,
                )
            case "double_click":
                button = button_map.get(getattr(action, "button", "left"), 1)
                docker_exec(
                    f"DISPLAY={vm.display} xdotool mousemove {action.x} {action.y} click --repeat 2 {button}",
                    vm.container_name,
                )
            case "scroll":
                button = 4 if getattr(action, "scrollY", 0) < 0 else 5
                clicks = max(1, abs(round(getattr(action, "scrollY", 0) / 100)))
                docker_exec(
                    f"DISPLAY={vm.display} xdotool mousemove {action.x} {action.y}",
                    vm.container_name,
                )
                for _ in range(clicks):
                    docker_exec(
                        f"DISPLAY={vm.display} xdotool click {button}",
                        vm.container_name,
                    )
            case "keypress":
                for key in action.keys:
                    normalized = "space" if key == "SPACE" else key
                    docker_exec(
                        f"DISPLAY={vm.display} xdotool key '{normalized}'",
                        vm.container_name,
                    )
            case "type":
                docker_exec(
                    f"DISPLAY={vm.display} xdotool type --delay 0 '{action.text}'",
                    vm.container_name,
                )
            case "wait":
                time.sleep(2)
            case "screenshot":
                pass
            case _:
                raise ValueError(f"Unsupported action: {action.type}")
            

def capture_screenshot(vm):
    return docker_exec(
        f"export DISPLAY={vm.display} && import -window root png:-",
        vm.container_name,
        decode=False,
    )