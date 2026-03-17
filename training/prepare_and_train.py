import os
import shutil
import random
from ultralytics import YOLO

def prepare_and_train():
    base_dir = r"C:\Users\samuv\Desktop\Programas_mios\LogiCheck\training"
    raw_dir = os.path.join(base_dir, "raw_frames")
    dataset_dir = os.path.join(base_dir, "dataset")
    
    # Paths for images and labels
    img_train = os.path.join(dataset_dir, "images", "train")
    img_val = os.path.join(dataset_dir, "images", "val")
    lbl_train = os.path.join(dataset_dir, "labels", "train")
    lbl_val = os.path.join(dataset_dir, "labels", "val")
    
    # Ensure directories exist
    for d in [img_train, img_val, lbl_train, lbl_val]:
        os.makedirs(d, exist_ok=True)
    
    # Find all labeled images
    labeled_images = []
    for file in os.listdir(raw_dir):
        if file.endswith(".jpg"):
            txt_file = file.replace(".jpg", ".txt")
            if os.path.exists(os.path.join(raw_dir, txt_file)):
                labeled_images.append(file)
                
    if len(labeled_images) == 0:
        print("==========================================================")
        print("ERROR: No se encontraron imágenes etiquetadas.")
        print("Por favor, abre 'labelImg', dibuja los cuadros sobre los bultos")
        print("y guarda los archivos .txt en la carpeta 'raw_frames'.")
        print("==========================================================")
        print("Para abrir labelImg, ejecuta en otra terminal:")
        print(f"labelImg {raw_dir}")
        return
        
    print(f"Encontradas {len(labeled_images)} imágenes etiquetadas. Preparando dataset...")
    
    # Split 80% train, 20% val
    random.shuffle(labeled_images)
    split_index = int(0.8 * len(labeled_images))
    train_files = labeled_images[:split_index]
    val_files = labeled_images[split_index:]
    
    def copy_files(file_list, target_img_dir, target_lbl_dir):
        for img_name in file_list:
            txt_name = img_name.replace(".jpg", ".txt")
            shutil.copy(os.path.join(raw_dir, img_name), os.path.join(target_img_dir, img_name))
            shutil.copy(os.path.join(raw_dir, txt_name), os.path.join(target_lbl_dir, txt_name))
            
    copy_files(train_files, img_train, lbl_train)
    copy_files(val_files, img_val, lbl_val)
    
    print(f"Dataset creado: {len(train_files)} para entrenamiento, {len(val_files)} para validación.")
    print("==========================================================")
    print("🚀 INICIANDO ENTRENAMIENTO CON YOLOv11 🚀")
    print("==========================================================")
    
    yaml_path = os.path.join(base_dir, "data.yaml")
    
    # Check GPU before training
    import torch
    device = "0" if torch.cuda.is_available() else "cpu"
    print(f"Entrenando en: {'GPU' if device == '0' else 'CPU'}")
    
    model = YOLO("yolo11n.pt")  # Use YOLO11 nano model
    model.train(
        data=yaml_path,
        epochs=50,
        imgsz=640,
        batch=16,
        device=device,
        project=os.path.join(base_dir, "runs"),
        name="bultos_cemento"
    )

if __name__ == "__main__":
    prepare_and_train()
