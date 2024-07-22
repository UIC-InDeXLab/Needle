import os
import shutil

from PIL import Image, ImageDraw, ImageFont


def create_test_image():
    image_size = (1000, 1000)
    background_color = "white"
    image = Image.new("RGB", image_size, background_color)

    draw = ImageDraw.Draw(image)
    cell_size = (image_size[0] // 4, image_size[1] // 4)
    font_size = 50

    # Use a default PIL font
    font = ImageFont.load_default(size=font_size)

    for i in range(4):
        for j in range(4):
            # Calculate the position for each cell
            top_left = (i * cell_size[0], j * cell_size[1])
            bottom_right = ((i + 1) * cell_size[0], (j + 1) * cell_size[1])

            # Draw the cell borders
            draw.rectangle([top_left, bottom_right], outline="black", width=5)

            # Calculate the position for the number
            number_position = (top_left[0] + cell_size[0] // 2, top_left[1] + cell_size[1] // 2)
            number_text = f"{i + 1 + j * 4}"
            bbox = draw.textbbox((0, 0), number_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            text_position = (number_position[0] - text_width // 2, number_position[1] - text_height // 2)

            # Draw the number in the center of the cell
            draw.text(text_position, number_text, fill="black", font=font)

    image.save("test_image.png")

def move_file(destination_path):
    source_path = "test_image.png"
    try:
        shutil.move(source_path, destination_path)
    except FileNotFoundError:
        print(f"Source file not found: {source_path}")
    except PermissionError:
        print(f"Permission denied while copying to: {destination_path}")
    except Exception as e:
        print(f"Error copying file: {e}")
