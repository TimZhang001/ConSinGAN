import datetime
import dateutil.tz
import os
import os.path as osp
from shutil import copyfile, copytree
import glob
import time
import random
import torch
import math

from ConSinGAN.config import get_arguments
import ConSinGAN.functions as functions

mvtectAD = "/raid/zhangss/dataset/ADetection/mvtecAD/"
mvtectTexture = ["grid", "carpet", "leather", "tile", "wood"]
mvtectObject1 = ["hazelnut", "bottle", "cable", "capsule",  "pill"] # , 
mvtectObject2 = ["screw", "metal_nut", "pill", "toothbrush", "transistor", "zipper"] #  
mvtectDebug   = ["zipper"] # 
mvtectAll     = mvtectTexture + mvtectObject1 + mvtectObject2

# noinspection PyInterpreter
if __name__ == '__main__':
    parser = get_arguments()
    parser.add_argument('--input_name', help='input image name for training', default="input.png")
    parser.add_argument('--naive_img',  help='naive input image  (harmonization or editing)', default="")
    parser.add_argument('--gpu', type=int, help='which GPU to use', default=5)
    parser.add_argument('--train_mode', default='generation',
                        choices=['generation', 'retarget', 'harmonization', 'editing', 'animation'],
                        help="generation, retarget, harmonization, editing, animation")
    parser.add_argument('--lr_scale',     type=float, help='scaling of learning rate for lower stages', default=0.1)
    parser.add_argument('--train_stages', type=int, help='how many stages to use for training', default=6)

    parser.add_argument('--fine_tune', action='store_true', help='whether to fine tune on a given image', default=0)
    parser.add_argument('--model_dir', help='model to be used for fine tuning (harmonization or editing)', default="")

    opt = parser.parse_args()

    for target in mvtectDebug: 
        opt         = functions.post_config(opt)
        target_path = os.path.join(mvtectAD, target, "test")
        file_names  = os.listdir(target_path)
        for file_name in file_names:
            if file_name not in ['squeezed_teeth']:
                continue

            opt.input_name = os.path.join(target_path, file_name, "000.png")
            opt.train_mode = "generation"
            opt.target     = target
            opt.subtarget  = file_name
    
    
            if opt.fine_tune:
                _gpu = opt.gpu
                _model_dir = opt.model_dir
                _timestamp = opt.timestamp
                _naive_img = opt.naive_img
                _niter = opt.niter

                opt = functions.load_config(opt)

                opt.gpu = _gpu
                opt.model_dir = _model_dir
                opt.start_scale = opt.train_stages - 1
                opt.timestamp = _timestamp
                opt.fine_tune = True
                opt.naive_img = _naive_img
                opt.niter = _niter

            if not os.path.exists(opt.input_name):
                print("Image does not exist: {}".format(opt.input_name))
                print("Please specify a valid image.")
                continue

            if torch.cuda.is_available():
                torch.cuda.set_device(opt.gpu)

            if opt.train_mode == "generation" or opt.train_mode == "retarget" or opt.train_mode == "animation":
                if opt.train_mode == "animation":
                    opt.min_size = 20
                from ConSinGAN.training_generation import *
            elif opt.train_mode == "harmonization" or opt.train_mode == "editing":
                if opt.fine_tune:
                    if opt.model_dir == "":
                        print("Model for fine tuning not specified.")
                        print("Please use --model_dir to define model location.")
                        exit()
                    else:
                        if not os.path.exists(opt.model_dir):
                            print("Model does not exist: {}".format(opt.model_dir))
                            print("Please specify a valid model.")
                            exit()
                    if not os.path.exists(opt.naive_img):
                        print("Image for harmonization/editing not found: {}".format(opt.naive_img))
                        exit()
                from ConSinGAN.training_harmonization_editing import *

            dir2save = functions.generate_dir2save_mvtec(opt)

            if osp.exists(dir2save):
                print('Trained model already exist: {}'.format(dir2save))
                #exit()
                continue

            # create log dir
            try:
                os.makedirs(dir2save)
            except OSError:
                pass

            # save hyperparameters and code files
            with open(osp.join(dir2save, 'parameters.txt'), 'w') as f:
                for o in opt.__dict__:
                    f.write("{}\t-\t{}\n".format(o, opt.__dict__[o]))
            current_path = os.path.dirname(os.path.abspath(__file__))
            for py_file in glob.glob(osp.join(current_path, "*.py")):
                copyfile(py_file, osp.join(dir2save, py_file.split("/")[-1]))
            copytree(osp.join(current_path, "ConSinGAN"), osp.join(dir2save, "ConSinGAN"))

            # train model
            print("Training model ({})".format(dir2save))
            start = time.time()
            train(opt)
            end = time.time()
            elapsed_time = end - start
            print("Time for training: {} seconds".format(elapsed_time))
