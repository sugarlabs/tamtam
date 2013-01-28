# useful methods to work with cairo in TamTam
from gi.repository import Gdk

def gdk_color_to_cairo(color):
    return (color.red / 65536.0, color.green / 65536.0, color.blue / 65536.0)

def get_gdk_color(str_color):
    result, color = Gdk.Color.parse(str_color)
    return color

def draw_round_rect(ctx, x, y, width, height, radio=20):
    # Move to A
    ctx.move_to(x + radio, y)
    # Straight line to B
    ctx.line_to(x + width - radio, y)
    # Curve to C, Control points are both at Q
    ctx.curve_to(x + width, y, x + width, y, x + width, y + radio)
    # Move to D
    ctx.line_to(x + width, y + height - radio)
    # Curve to E
    ctx.curve_to(x + width, y + height, x + width, y + height,
            x + width - radio, y + height)
    # Line to F
    ctx.line_to(x + radio, y + height)
    # Curve to G
    ctx.curve_to(x, y + height, x, y + height, x, y + height - radio)
    # Line to H
    ctx.line_to(x, y + radio)
    # Curve to A
    ctx.curve_to(x, y, x, y, x + radio, y)

def draw_drum_mask(ctx, x, y, size):
    side = size / 4
    ctx.move_to(x + side, y)
    ctx.new_path()
    ctx.line_to(x + size - side, y)
    ctx.line_to(x + size, y + side)
    ctx.line_to(x + size, y + size - side)
    ctx.line_to(x + size - side, y + size)
    ctx.line_to(x + side, y + size)
    ctx.line_to(x, y + size - side)
    ctx.line_to(x, y + side)
    ctx.line_to(x + side, y)
    ctx.close_path()

def draw_loop_mask(ctx, x, y, width, height, radio=20):
    # Move to A
    ctx.move_to(x, y)
    # Straight line to B
    ctx.line_to(x + width - radio, y)
    # Curve to C, Control points are both at Q
    ctx.curve_to(x + width, y, x + width, y, x + width, y + radio)
    # Move to D
    ctx.line_to(x + width, y + height - radio)
    # Curve to E
    ctx.curve_to(x + width, y + height, x + width, y + height,
            x + width - radio, y + height)
    # Line to F
    ctx.line_to(x, y + height)
    radio = radio / 3
    # Curve to G
    ctx.curve_to(x - radio, y + height,
                x + radio, y + height,
                x + radio, y + height - radio)
    # Line to H
    ctx.line_to(x + radio, y + radio)
    # Curve to A
    ctx.curve_to(x + radio, y, x, y, x - radio, y)
