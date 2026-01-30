#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MangaBuff Alliance Monitor
Мониторинг смены тайтла в альянсе
"""

from monitor import MangaBuffMonitor

def main():
    print("""
╔═══════════════════════════════════════════╗
║   MangaBuff Alliance Monitor v1.0         ║
║   Мониторинг смены тайтла в альянсе       ║
╚═══════════════════════════════════════════╝
    """)
    
    monitor = MangaBuffMonitor()
    monitor.start()

if __name__ == "__main__":
    main()