from PIL import Image, ImageEnhance
import os
import random
import time

def process_image_anti_ban(input_path, output_dir):
    """
    Aplica pequenas modificações na imagem para alterar o hash MD5 
    e evitar detecção por sistemas anti-spam do WhatsApp.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    filename = os.path.basename(input_path)
    # Gera um nome único para evitar colisões
    output_filename = f"mod_{int(time.time())}_{filename}"
    output_path = os.path.join(output_dir, output_filename)
    
    try:
        with Image.open(input_path) as img:
            # 1. Converte para RGB se necessário (remover canais Alpha que podem denunciar edição)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            # 2. Leve alteração de brilho (imperceptível)
            enhancer = ImageEnhance.Brightness(img)
            # Fator entre 0.99 e 1.01
            factor = 1.0 + (random.uniform(-0.01, 0.01))
            img = enhancer.enhance(factor)
            
            # 3. Adiciona um único pixel de ruído no canto (opcional, mas altera o hash)
            # pixels = img.load()
            # r, g, b = pixels[0, 0]
            # pixels[0, 0] = (r, g, (b+1)%255)
            
            # 4. Salva com uma qualidade levemente variada para forçar novo encoding
            quality = random.randint(92, 98)
            img.save(output_path, "JPEG", quality=quality, optimize=True)
            
        return output_path
    except Exception as e:
        print(f"Erro ao processar imagem: {e}")
        return input_path # Fallback para a original em caso de erro
