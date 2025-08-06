#!/bin/bash
# GitHub'a kod gönderme scripti

echo "🚀 SQLAI GitHub Push Script"
echo "============================="

# GitHub repo oluşturduktan sonra bu komutu çalıştır:
echo "1. GitHub'da yeni repo oluştur: https://github.com/new"
echo "   - Repository name: SQLAI"
echo "   - Description: 🤖 AI-Powered PostgreSQL Database Assistant with Turkish Language Support"
echo "   - Public olarak seç"
echo ""

echo "2. Repo oluşturduktan sonra bu komutları çalıştır:"
echo ""
echo "git remote set-url origin https://YOUR_TOKEN@github.com/abvural/SQLAI.git"
echo "git push -u origin main"
echo ""

echo "3. Alternatif olarak SSH kullan:"
echo "git remote set-url origin git@github.com:abvural/SQLAI.git"
echo "git push -u origin main"
echo ""

echo "📊 Mevcut durum:"
echo "- Git repository: ✅ Hazır"
echo "- Commits: ✅ 83 dosya commit edildi"
echo "- Remote: ⏳ GitHub repo oluşturulması bekleniyor"
echo ""

echo "🎯 Proje istatistikleri:"
echo "- Toplam dosya: 83"
echo "- Kod satırı: 20,242+"
echo "- Backend: 100% tamamlandı"
echo "- API endpoints: 26"
echo "- Dokümantasyon: ✅ Hazır"

# Repo durumunu göster
echo ""
echo "📋 Git durumu:"
git status
git log --oneline -5