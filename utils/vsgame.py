class TeamCOlors:
    RED = "🔴"
    BLUE = "🔵"
    GREEN = "🟢"
    YELLOW = "🟡"
    PURPLE = "🟣"
    ORANGE = "🟠"
    BLACK = "⚫"
    WHITE = "⚪"
    BROWN = "🟤"

    def all_color_names():
        return ["red", "blue", "green", "yellow", "purple", "orange", "black", "white", "brown"]
    def all_colors_dict():
        return {
            "red": TeamCOlors.RED,
            "blue": TeamCOlors.BLUE,
            "green": TeamCOlors.GREEN,
            "yellow": TeamCOlors.YELLOW,
            "purple": TeamCOlors.PURPLE,
            "orange": TeamCOlors.ORANGE,
            "black": TeamCOlors.BLACK,
            "white": TeamCOlors.WHITE,
            "brown": TeamCOlors.BROWN
        }