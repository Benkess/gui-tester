# playwrite-based Computer Use Example Tool
# Actions supported: click, double_click, scroll, type, wait, keypress, drag, move, screenshot


import time


def handle_computer_actions(page, actions):
    for action in actions:
        match action.type:
            case "click":
                page.mouse.click(
                    action.x,
                    action.y,
                    button=getattr(action, "button", "left"),
                )
            case "double_click":
                page.mouse.dblclick(
                    action.x,
                    action.y,
                    button=getattr(action, "button", "left"),
                )
            case "scroll":
                page.mouse.move(action.x, action.y)
                page.mouse.wheel(
                    getattr(action, "scrollX", 0),
                    getattr(action, "scrollY", 0),
                )
            case "keypress":
                for key in action.keys:
                    page.keyboard.press(" " if key == "SPACE" else key)
            case "type":
                page.keyboard.type(action.text)
            case "wait":
                time.sleep(2)
            case "screenshot":
                pass
            case _:
                raise ValueError(f"Unsupported action: {action.type}")
            

def capture_screenshot(page):
    return page.screenshot(type="png")