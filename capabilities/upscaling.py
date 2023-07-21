import cv2
import argparse
import os
import numpy as np
from scipy.signal import wiener


def parse():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pic', help="Path to picture.", default=False, const=True, nargs='?')
    parser.add_argument('--dest', help="Destination to save upscaled image to.", default=None)

    return parser.parse_args()


def deblur_image(image):
    # Apply the Wiener filter to each color channel
    deblurred = np.zeros_like(image)
    for i in range(3):
        deblurred[:, :, i] = wiener(image[:, :, i])

    return deblurred


def upscale_image(input_path, output_path=None):
    print(input_path)
    if output_path is None:
        picname = os.path.basename(input_path)
        output_path = f'outputs/upscaled\\{os.path.splitext(picname)[0]}_upscaled{os.path.splitext(picname)[1]}'

    # Read the image
    img = cv2.imread(input_path)

    # Deblur the image
    deblurred = deblur_image(img)

    # Double the size of the image
    upscale_size = (deblurred.shape[1] * 2, deblurred.shape[0] * 2)

    # Perform the upsampling
    upscaled = cv2.resize(deblurred, upscale_size, interpolation=cv2.INTER_CUBIC)

    # Save the upscaled image
    cv2.imwrite(output_path, upscaled)

    print(f"Upscaled image saved at {output_path}")


def main():
    args = parse()
    upscale_image(args.pic, args.dest)


if __name__ == '__main__':
    main()
