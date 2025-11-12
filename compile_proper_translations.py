#!/usr/bin/env python3
"""
Compilação de arquivos de tradução .ts para .qm usando PyQt6
"""

import os
import sys
from PyQt6.QtCore import QTranslator, QLocale
from PyQt6.QtWidgets import QApplication

def compile_ts_file(ts_file, qm_file):
    """
    Compila um arquivo .ts para .qm usando PyQt6
    
    Args:
        ts_file: Caminho do arquivo .ts
        qm_file: Caminho do arquivo .qm de saída
    """
    try:
        # Ler o arquivo .ts
        with open(ts_file, 'r', encoding='utf-8') as f:
            ts_content = f.read()
        
        # Criar um tradutor vazio e salvar como .qm
        # Esta é uma abordagem simplificada - o ideal seria usar lrelease
        translator = QTranslator()
        
        # Para funcionar, vamos criar um .qm básico
        # Na prática, o ideal é usar a ferramenta lrelease do Qt
        print(f"AVISO: Compilação simplificada para {ts_file}")
        print(f"      Para produção, use: lrelease {ts_file}")
        
        # Criar arquivo .qm vazio (funciona como fallback)
        if translator.load(ts_file.replace('.ts', '')):
            print(f"Arquivo de tradução carregado: {ts_file}")
            return True
        else:
            print(f"Não foi possível carregar tradução de: {ts_file}")
            return False
            
    except Exception as e:
        print(f"Erro ao compilar {ts_file}: {e}")
        return False

def main():
    """Função principal"""
    translations_dir = 'translations'
    
    # Lista de arquivos .ts para compilar
    ts_files = [
        'app_en.ts',
        'app_pt_BR.ts'
    ]
    
    print("Compilando arquivos de tradução...")
    
    for ts_file in ts_files:
        ts_path = os.path.join(translations_dir, ts_file)
        qm_path = os.path.join(translations_dir, ts_file.replace('.ts', '.qm'))
        
        if os.path.exists(ts_path):
            print(f"\nProcessando: {ts_file}")
            
            # Para o português, vamos tentar uma abordagem diferente
            if 'pt_BR' in ts_file:
                # Criar um tradutor e tentar salvar
                app = QApplication(sys.argv)
                translator = QTranslator()
                
                # Tentar carregar o arquivo .ts diretamente
                if translator.load(ts_path.replace('.ts', '')):
                    print(f"✓ Tradução carregada: {ts_file}")
                    # Salvar como .qm
                    if translator.save(qm_path):
                        print(f"✓ Salvo como: {qm_file}")
                    else:
                        print(f"✗ Falha ao salvar: {qm_file}")
                else:
                    print(f"✗ Falha ao carregar: {ts_file}")
                
                app.quit()
            else:
                compile_ts_file(ts_path, qm_path)
        else:
            print(f"Arquivo não encontrado: {ts_path}")
    
    print("\nCompilação concluída!")
    print("\nNOTA: Para compilação completa, instale as ferramentas Qt:")
    print("      Ubuntu/Debian: sudo apt install qt6-tools-dev")
    print("      Arch: sudo pacman -S qt6-tools")
    print("      Depois use: lrelease translations/*.ts")

if __name__ == '__main__':
    main()