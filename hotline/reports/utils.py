import logging
import os
from PIL import Image, ImageDraw, ImageFilter


log = logging.getLogger(__name__)


def generate_icon(output_path,
        icon=None,
        color='#999',
        generated_icon_size=(30, 45),
        square_coords=[(0, 0), (30, 30)],
        triangle_coords=[(10, 30), (15, 45), (20, 30)],
        icon_offset=(0, -10),
        transparent=(0,0,0,0),
        outline_color=(10,10,10,255)):
    """Generate pin icon for this report.

    If no icon or color is specified, then a grey pin icon with no inner icon will be created.
     ____
    |    |  <- Icons look like this and are constructed in the following way:
    | $$ |      + A transparent canvas is created to hold the icon.
    |_  _|      + A square is placed in the canvas so that it is aligned with the top.
      \/        + And an inverted triangle is placed directly under the square to complete the background.
                + The outline of the two shapes is extracted and converted to the correct color.
                + The icon image is pasted in the center of a transparent canvas.
                + And the canvas is pasted in the middle of the background.
                + And finally, the outline is merged on top of the background.
    """
    # Define the color mode (because the mode has to
    # be the same in order to merge images)
    mode = 'RGBA'

    # Create a new, transparent image as a canvas with the defined mode and size.
    canvas = Image.new(mode, generated_icon_size, transparent)

    # Draw the background for the icon
    background = ImageDraw.Draw(canvas)
    background.rectangle(square_coords, fill=color)
    background.polygon(triangle_coords, fill=color)

    # Filter out the edges if the background and add a
    # nice dark outline to it by traversing pixel by pixel.
    outline = canvas.filter(ImageFilter.FIND_EDGES)
    pixels = outline.load()
    for i in range(outline.size[0]):
        for j in range(outline.size[1]):
            if pixels[i,j] != transparent:
                # Since our canvas is transparent, any pixel that
                # isn't transparent is guaranteed to be an edge, and
                # thus should have it's color changed to the outline color.
                pixels[i,j] = outline_color

    img = canvas
    if icon and os.path.exists(icon.path):
        # Before we can use the icon, it needs to be
        # pasted into an image with the same properties
        # as the background image. Otherwise, transparency
        # will not be preserved. To do this we simply create a new image with
        # the same properties as the canvas, and paste the icon into it.
        icon_file = Image.open(icon.path)
        icon_canvas = Image.new(mode, generated_icon_size)
        icon_canvas.paste(icon_file, icon_offset)

        # Alpha composite merge is used to ensure transparency
        # is preserved while moving the icon onto the canvas.
        img = Image.alpha_composite(canvas, icon_canvas)
    else:
        log.warn('No icon found for this category')

    # Now merge the image with the outline
    img = Image.alpha_composite(img, outline)

    try:
        img.save(output_path)
    except IOError as e:
        log.warn('Error while saving icon image')

