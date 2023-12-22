import argparse, multiprocessing
import cv2
import glob
import numpy as np
import os
import torch
from basicsr.utils import imwrite
#from multiprocessing import ProcessingPool as Pool
from gfpgan import GFPGANer
from time import perf_counter

parser = argparse.ArgumentParser()
parser.add_argument(
    '-i',
    '--input',
    type=str,
    default='inputs/whole_imgs',
    help='Input image or folder. Default: inputs/whole_imgs')
parser.add_argument('-o', '--output', type=str, default='results_mulPro', help='Output folder. Default: results')
# we use version to select models, which is more user-friendly
parser.add_argument(
    '-v', '--version', type=str, default='1.3', help='GFPGAN model version. Option: 1 | 1.2 | 1.3. Default: 1.3')
parser.add_argument(
    '-s', '--upscale', type=int, default=2, help='The final upsampling scale of the image. Default: 2')

parser.add_argument(
    '--bg_upsampler', type=str, default='realesrgan', help='background upsampler. Default: realesrgan')
parser.add_argument(
    '--bg_tile',
    type=int,
    default=400,
    help='Tile size for background sampler, 0 for no tile during testing. Default: 400')
parser.add_argument('--suffix', type=str, default=None, help='Suffix of the restored faces')
parser.add_argument('--only_center_face', action='store_true', help='Only restore the center face')
parser.add_argument('--aligned', action='store_true', help='Input are aligned faces')
parser.add_argument(
    '--ext',
    type=str,
    default='auto',
    help='Image extension. Options: auto | jpg | png, auto means using the same extension as inputs. Default: auto')
parser.add_argument('-w', '--weight', type=float, default=0.5, help='Adjustable weights.')
args = parser.parse_args()


# ------------------------ set up GFPGAN restorer ------------------------
if args.version == '1':
    arch = 'original'
    channel_multiplier = 1
    model_name = 'GFPGANv1'
    url = 'https://github.com/TencentARC/GFPGAN/releases/download/v0.1.0/GFPGANv1.pth'
elif args.version == '1.2':
    arch = 'clean'
    channel_multiplier = 2
    model_name = 'GFPGANCleanv1-NoCE-C2'
    url = 'https://github.com/TencentARC/GFPGAN/releases/download/v0.2.0/GFPGANCleanv1-NoCE-C2.pth'
elif args.version == '1.3':
    arch = 'clean'
    channel_multiplier = 2
    model_name = 'GFPGANv1.3'
    url = 'https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.3.pth'
elif args.version == '1.4':
    arch = 'clean'
    channel_multiplier = 2
    model_name = 'GFPGANv1.4'
    url = 'https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth'
elif args.version == 'RestoreFormer':
    arch = 'RestoreFormer'
    channel_multiplier = 2
    model_name = 'RestoreFormer'
    url = 'https://github.com/TencentARC/GFPGAN/releases/download/v1.3.4/RestoreFormer.pth'
else:
    raise ValueError(f'Wrong model version {args.version}.')


# ------------------------ set up background upsampler ------------------------
if args.bg_upsampler == 'realesrgan':
    if not torch.cuda.is_available():  # CPU
        import warnings
        warnings.warn('The unoptimized RealESRGAN is slow on CPU. We do not use it. '
                        'If you really want to use it, please modify the corresponding codes.')
        bg_upsampler = None
    else:
        from basicsr.archs.rrdbnet_arch import RRDBNet
        from realesrgan import RealESRGANer
        model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=2)
        bg_upsampler = RealESRGANer(
            scale=2,
            model_path='https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth',
            model=model,
            tile=args.bg_tile,
            tile_pad=10,
            pre_pad=0,
            half=True)  # need to set False in CPU mode
else:
    bg_upsampler = None


# determine model paths
model_path = os.path.join('experiments/pretrained_models', model_name + '.pth')
if not os.path.isfile(model_path):
    model_path = os.path.join('gfpgan/weights', model_name + '.pth')
if not os.path.isfile(model_path):
    # download pre-trained models from url
    model_path = url
restorer = GFPGANer(
    model_path=model_path,
    upscale=args.upscale,
    arch=arch,
    channel_multiplier=channel_multiplier,
    bg_upsampler=bg_upsampler)


def restore_mul(img_path):
        # read image
        img_name = os.path.basename(img_path)
        print(f'Processing {img_name} ...')
        basename, ext = os.path.splitext(img_name)
        input_img = cv2.imread(img_path, cv2.IMREAD_COLOR)

        # restore faces and background if necessary
        cropped_faces, restored_faces, restored_img = restorer.enhance(
            input_img,
            has_aligned=args.aligned,
            only_center_face=args.only_center_face,
            paste_back=True,
            weight=args.weight)
        # save restored img
        if restored_img is not None:
            if args.ext == 'auto':
                extension = ext[1:]
            else:
                extension = args.ext

            if args.suffix is not None:
                save_restore_path = os.path.join(args.output, 'restored_imgs', f'{basename}_{args.suffix}.{extension}')
            else:
                save_restore_path = os.path.join(args.output, 'restored_imgs', f'{basename}.{extension}')
            imwrite(restored_img, save_restore_path)



def main():
    """Inference demo for GFPGAN (for users).
    """
    stratInf = perf_counter()
    global args
    global restorer

    # ------------------------ input & output ------------------------
    if args.input.endswith('/'):
        args.input = args.input[:-1]
    if os.path.isfile(args.input):
        img_list = [args.input]
    else:
        img_list = sorted(glob.glob(os.path.join(args.input, '*')))

    os.makedirs(args.output, exist_ok=True)

    #112 / 16
    # ------------------------ restore ------------------------
    ctx = torch.multiprocessing.get_context("spawn")
    pool = ctx.Pool(7)
    pool.map(restore_mul, img_list)
    endInf = perf_counter()

    print(f"Inferenece Time in multiprocessing: {endInf - stratInf}")

    #print(f'Results are in the [{args.output}] folder.')


if __name__ == '__main__':
    main()
