# 🚀 Hosting Configuration Guide
## Fix for Environment Variables Issue

### 🔍 Current Issue
Your health check is showing:
```json
{
  "status": "healthy",
  "timestamp": "2025-09-09T01:21:42.307Z", 
  "environment": "development",
  "database": "SQLite"
}
```

This indicates that the hosting platform is **NOT** properly configured with production environment variables.

---

## 🛠️ Platform-Specific Configuration

### 1. 🟢 **Render.com Configuration**

#### Step 1: Access Environment Variables
1. Go to your Render.com dashboard
2. Select your `sajjaly-pro` service
3. Click on **"Environment"** tab
4. Click **"Add Environment Variable"**

#### Step 2: Add Required Variables
```bash
# REQUIRED - Set Environment to Production
NODE_ENV=production

# REQUIRED - PostgreSQL Database (Get from Supabase or Render PostgreSQL)
DATABASE_URL=postgresql://username:password@host:5432/database

# REQUIRED - JWT Secret (Generate a secure random string)
JWT_SECRET=your_super_secure_random_string_here_at_least_32_characters_long

# OPTIONAL - Platform Detection
RENDER=true

# OPTIONAL - Timezone
TZ=Asia/Baghdad
```

#### Step 3: Generate Secure JWT Secret
Run this command locally to generate a secure JWT secret:
```bash
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
```

#### Step 4: Database Setup Options

**Option A: Use Render PostgreSQL (Paid)**
1. In Render dashboard, create a new PostgreSQL instance
2. Copy the connection string
3. Set it as `DATABASE_URL`

**Option B: Use Supabase (Free)**
1. Go to [supabase.com](https://supabase.com)
2. Create new project
3. Get connection string from Settings → Database
4. Format: `postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres`

---

### 2. 🔵 **Railway.app Configuration**

#### Step 1: Add Environment Variables
```bash
NODE_ENV=production
DATABASE_URL=postgresql://username:password@host:5432/database
JWT_SECRET=your_super_secure_random_string_here
RAILWAY_ENVIRONMENT=true
TZ=Asia/Baghdad
```

#### Step 2: Database Plugin
1. In Railway dashboard, click **"+ New"**
2. Select **"Database"** → **"PostgreSQL"**
3. Railway will automatically provide `DATABASE_URL`

---

### 3. 🟡 **Vercel.com Configuration**

#### Step 1: Environment Variables
1. Go to Vercel dashboard
2. Select your project
3. Go to **Settings** → **Environment Variables**

```bash
NODE_ENV=production
DATABASE_URL=postgresql://username:password@host:5432/database
JWT_SECRET=your_super_secure_random_string_here
VERCEL=true
```

#### Note: Vercel Limitations
- Vercel is serverless - database connections may timeout
- Better to use Supabase for database with Vercel
- File uploads will use memory storage (temporary)

---

### 4. 🟣 **Heroku Configuration**

#### Using Heroku CLI:
```bash
heroku config:set NODE_ENV=production
heroku config:set JWT_SECRET=your_super_secure_random_string_here
heroku config:set TZ=Asia/Baghdad

# Add PostgreSQL
heroku addons:create heroku-postgresql:hobby-dev
```

---

## 🔧 **Quick Fix Steps**

### Step 1: Set NODE_ENV
**This is the most important step!**
```bash
NODE_ENV=production
```

### Step 2: Configure Database
Choose one option:

**Option A: Supabase (Recommended - Free)**
```bash
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
```

**Option B: Platform Database**
- Render: Add PostgreSQL service
- Railway: Add PostgreSQL plugin  
- Heroku: `heroku addons:create heroku-postgresql`

### Step 3: Secure JWT Secret
```bash
JWT_SECRET=a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456
```

### Step 4: Deploy & Verify
After setting environment variables:
1. **Redeploy** your application
2. Visit: `https://your-app-url/health`
3. Should show:
```json
{
  "status": "healthy",
  "environment": "production", 
  "database": "PostgreSQL",
  "platform": {
    "detected": "Render.com"  // or your platform
  },
  "configuration": {
    "hasPostgreSQL": true,
    "hasJWTSecret": true, 
    "isProduction": true
  },
  "warnings": []
}
```

---

## 🚨 **Common Issues & Solutions**

### Issue 1: Still Showing "development"
**Solution:** Redeploy after setting `NODE_ENV=production`

### Issue 2: Still Using SQLite  
**Solution:** Set `DATABASE_URL` with valid PostgreSQL connection string

### Issue 3: Database Connection Errors
**Solution:** 
- Verify DATABASE_URL format
- Check database server is running
- Ensure IP whitelist includes hosting platform

### Issue 4: JWT Secret Warnings
**Solution:** Generate secure random string (32+ characters)

---

## 🔍 **Enhanced Health Check**

Your app now has an enhanced health check. Visit:
- `https://your-app/health` - Basic health info
- `https://your-app/health?debug=true` - Detailed debug info

The debug version shows:
- All environment variable status
- Platform detection
- Memory usage
- Configuration warnings
- Detailed diagnostics

---

## ✅ **Verification Checklist**

After configuration, verify:
- [ ] `NODE_ENV` = "production" 
- [ ] `DATABASE_URL` configured
- [ ] `JWT_SECRET` set (not default)
- [ ] Health check shows "PostgreSQL"
- [ ] Platform detected correctly
- [ ] No warnings in health check
- [ ] App functions correctly

---

## 🆘 **Need Help?**

If you're still seeing issues:

1. **Check the debug health endpoint:**
   ```
   https://your-app-url/health?debug=true
   ```

2. **Verify environment variables are set correctly on your platform**

3. **Redeploy after making changes**

4. **Check platform-specific logs for errors**

Your app is now ready for production! 🎉