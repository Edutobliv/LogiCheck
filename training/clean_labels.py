import os
import glob

raw_dir = r"C:\Users\samuv\Desktop\Programas_mios\LogiCheck\training\raw_frames"
txt_files = glob.glob(os.path.join(raw_dir, "*.txt"))

count = 0
for txt in txt_files:
    if "classes.txt" in txt.lower():
        # Overwrite classes.txt to just have 'bulto'
        with open(txt, "w") as f:
            f.write("bulto\n")
        continue

    with open(txt, "r") as f:
        lines = f.readlines()
        
    new_lines = []
    for line in lines:
        parts = line.strip().split()
        if len(parts) >= 5:
            # Force class ID to 0 (bulto)
            parts[0] = "0"
            new_lines.append(" ".join(parts) + "\n")
            
    if new_lines:
        with open(txt, "w") as f:
            f.writelines(new_lines)
        count += 1

print(f"Limpiadas {count} imágenes con etiquetas.")
