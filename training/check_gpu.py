import torch
import ultralytics

print(f"PyTorch version: {torch.__version__}")
print(f"Ultralytics version: {ultralytics.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
else:
    print("Warning: CUDA is NOT available. Training will be slow on CPU. Please visit pytorch.org to install the CUDA version.")
