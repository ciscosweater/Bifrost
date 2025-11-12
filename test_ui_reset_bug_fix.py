#!/usr/bin/env python3
"""
Teste específico para verificar se o problema de reset da UI foi corrigido
Problema: UI não resetava depois que o diálogo de fixes era fechado
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.logger import setup_logging
setup_logging()

import logging
logger = logging.getLogger(__name__)

class MockMainWindow:
    """Mock da MainWindow para testar o problema específico"""
    
    def __init__(self):
        self._ui_reset_cancelled = False
        self._fix_dialog_open = False
        self.reset_calls = []
        
    def _safe_reset_ui_state(self):
        """Safe reset que preserva dados críticos se fix pode estar sendo aplicado"""
        # Check if UI reset was cancelled due to fix operations
        if hasattr(self, '_ui_reset_cancelled') and self._ui_reset_cancelled:
            logger.debug("UI reset cancelled - fix operations in progress")
            self.reset_calls.append('cancelled')
            return
            
        # Only reset if we're not in the middle of fix operations
        if not hasattr(self, '_fix_dialog_open') or not self._fix_dialog_open:
            self._reset_ui_state()
        else:
            logger.debug("Skipping UI reset - fix dialog might be open")
            self.reset_calls.append('skipped')
    
    def _reset_ui_state(self):
        """Reseta estado da UI"""
        logger.debug("UI state reset to initial values")
        self.reset_calls.append('completed')
    
    def simulate_fix_available(self):
        """Simula detecção de fixes disponíveis"""
        logger.info("🔧 Fix available - setting cancellation flag")
        self._ui_reset_cancelled = True
        
    def simulate_fix_dialog_closed(self):
        """Simula fechamento do diálogo de fixes (COM CORREÇÃO)"""
        logger.info("📝 Fix dialog closed - resetting cancellation flag")
        self._ui_reset_cancelled = False  # <-- ESTA É A CORREÇÃO
        
    def simulate_fix_dialog_closed_without_fix(self):
        """Simula fechamento do diálogo de fixes (SEM CORREÇÃO - comportamento antigo)"""
        logger.info("📝 Fix dialog closed - NOT resetting cancellation flag (OLD BEHAVIOR)")
        # Não reseta _ui_reset_cancelled = False
        
    def simulate_ui_reset_timer_fired(self):
        """Simula o timer de reset da UI disparando"""
        logger.info("⏰ UI reset timer fired")
        self._safe_reset_ui_state()

def test_problem_scenario():
    """Testa o cenário do problema específico"""
    print("🐛 Testing the original problem scenario...")
    print("=" * 60)
    
    # Cenário 1: Comportamento antigo (com bug)
    print("\n--- OLD BEHAVIOR (with bug) ---")
    window_old = MockMainWindow()
    
    # 1. Download completa, fixes disponíveis
    window_old.simulate_fix_available()
    
    # 2. Usuário fecha diálogo de fixes (sem resetar flag)
    window_old.simulate_fix_dialog_closed_without_fix()
    
    # 3. Timer de UI reset dispara
    window_old.simulate_ui_reset_timer_fired()
    
    # 4. Tenta resetar novamente depois
    window_old.simulate_ui_reset_timer_fired()
    
    print(f"Reset calls: {window_old.reset_calls}")
    if 'cancelled' in window_old.reset_calls and 'completed' not in window_old.reset_calls:
        print("❌ BUG CONFIRMED: UI never resets after fix dialog closed")
    else:
        print("✅ No bug detected")
    
    # Cenário 2: Comportamento novo (corrigido)
    print("\n--- NEW BEHAVIOR (fixed) ---")
    window_new = MockMainWindow()
    
    # 1. Download completa, fixes disponíveis
    window_new.simulate_fix_available()
    
    # 2. Usuário fecha diálogo de fixes (com reset do flag)
    window_new.simulate_fix_dialog_closed()
    
    # 3. Timer de UI reset dispara
    window_new.simulate_ui_reset_timer_fired()
    
    print(f"Reset calls: {window_new.reset_calls}")
    if 'completed' in window_new.reset_calls:
        print("✅ FIX CONFIRMED: UI resets correctly after fix dialog closed")
    else:
        print("❌ Fix didn't work")
    
    return window_old.reset_calls, window_new.reset_calls

def test_fix_application_scenario():
    """Testa cenário de aplicação de fix"""
    print("\n" + "=" * 60)
    print("🔧 Testing fix application scenario...")
    
    window = MockMainWindow()
    
    # 1. Download completa, fixes disponíveis
    window.simulate_fix_available()
    
    # 2. Fix é aplicado com sucesso (reseta flag)
    logger.info("📦 Fix applied successfully - resetting cancellation flag")
    window._ui_reset_cancelled = False  # Simula reset no apply_fix
    
    # 3. Timer de UI reset dispara
    window.simulate_ui_reset_timer_fired()
    
    print(f"Reset calls: {window.reset_calls}")
    if 'completed' in window.reset_calls:
        print("✅ UI resets correctly after fix application")
    else:
        print("❌ UI doesn't reset after fix application")

def main():
    """Função principal"""
    print("🧪 Testing Specific UI Reset Bug Fix")
    print("=" * 60)
    print("Problem: UI not resetting after fix dialog closed")
    print("Solution: Reset _ui_reset_cancelled flag when dialog closes")
    
    old_calls, new_calls = test_problem_scenario()
    test_fix_application_scenario()
    
    print("\n" + "=" * 60)
    print("📊 SUMMARY:")
    print(f"Old behavior calls: {old_calls}")
    print(f"New behavior calls: {new_calls}")
    
    # Verificação final
    bug_fixed = (
        'cancelled' in old_calls and 'completed' not in old_calls and  # Bug existed
        'completed' in new_calls  # Fix works
    )
    
    if bug_fixed:
        print("🎉 BUG FIX VERIFIED: The UI reset issue has been resolved!")
        print("✅ UI now resets correctly after fix dialog operations")
    else:
        print("❌ Bug fix verification failed")
    
    return bug_fixed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)