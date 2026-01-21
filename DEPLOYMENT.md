# 🚀 Deployment Guide - Sajjaly Pro School Management System

## ❌ Why GitHub Pages Doesn't Work
GitHub Pages only serves static files and cannot run:
- Python server (`server.py`)
- SQLite database
- API endpoints

## ✅ Recommended Deployment Platforms

### 1. 🚂 **Railway** (Easiest - Recommended)

**Steps:**
1. Push your code to GitHub
2. Go to [Railway.app](https://railway.app)
3. Sign up with GitHub
4. Click "New Project" → "Deploy from GitHub repo"
5. Select your repository
6. Railway will automatically detect Python and deploy

**Environment Variables** (Optional):
- `JWT_SECRET`: `your_super_secret_key_change_in_production`
- `NODE_ENV`: `production`

### 2. 🎨 **Render** (Free Tier)

**Steps:**
1. Push code to GitHub
2. Go to [Render.com](https://render.com)
3. Sign up with GitHub
4. New → Web Service
5. Connect your repository
6. Configure:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python server.py`
   - **Python Version**: 3.9+

### 3. ▲ **Vercel** (Requires Modification)

**Steps:**
1. Install Vercel CLI: `npm i -g vercel` (or `pip install vercel`)
2. In project directory: `vercel --prod`
3. Follow prompts

**Note**: May require database adjustments for serverless

### 4. 📱 **Heroku** (Paid Plans Only)

**Steps:**
1. Install Heroku CLI
2. `heroku create your-app-name`
3. `git push heroku main`

## 📂 Pre-Deployment Checklist

✅ Files created:
- `railway.json` - Railway configuration
- `render.yaml` - Render configuration  
- `vercel.json` - Vercel configuration
- `package.json` - Updated with production scripts

✅ Code updates:
- CORS configured for production domains
- Database initialization on deployment
- Environment variables support

## 🔧 Local Testing for Production

```bash
# Set production environment
set NODE_ENV=production  # Windows
export NODE_ENV=production  # Linux/Mac

# Test production
python server.py
```

## 🌐 After Deployment

1. **Update CORS origins** in `server.py` with your actual domain
2. **Test all features**:
   - Admin login (username: admin, password: admin123)
   - School registration and login
   - Student management
   - Grades and attendance

## 🔑 Default Credentials

- **Admin**: username: `admin`, password: `admin123`
- **First School**: Will be created via admin dashboard
- **Students**: Use generated codes from school dashboard

## ⚠️ Security Notes

- Change default admin password after deployment
- Use strong JWT_SECRET in production
- Enable HTTPS (automatic on most platforms)

## 🆘 Troubleshooting

**404 Errors**: Check if backend is running
**Database Errors**: Ensure SQLite permissions
**CORS Errors**: Update origins in server.js
**Build Failures**: Check Python version (3.8+)

## 📞 Support

The application will be available at your deployment URL:
- Railway: `https://your-app-name.railway.app`
- Render: `https://your-app-name.onrender.com`
- Vercel: `https://your-app-name.vercel.app`