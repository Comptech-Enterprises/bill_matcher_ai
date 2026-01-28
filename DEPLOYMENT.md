# 🚀 Render Deployment Guide

## Prerequisites
- [x] GitHub account
- [x] Render account (sign up at https://render.com)
- [x] NVIDIA API key for NIM service

---

## Quick Start (Using render.yaml)

### Step 1: Push to GitHub
```bash
git add .
git commit -m "Prepare for Render deployment"
git push origin main
```

### Step 2: Deploy on Render
1. Go to https://dashboard.render.com
2. Click **"New +"** → **"Blueprint"**
3. Connect your GitHub repository
4. Render will detect `render.yaml` and configure both services automatically
5. Set the `NVIDIA_API_KEY` environment variable in the backend service

---

## Manual Deployment (Step-by-Step)

### Part 1: Deploy Backend

#### 1. Create Web Service
1. Go to https://dashboard.render.com
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Configure:
   - **Name:** `bill-matcher-backend`
   - **Region:** US East (Ohio) or closest to your users
   - **Branch:** `main`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `cd backend && python app.py`

#### 2. Set Environment Variables
Click "Environment" and add:

| Variable | Value | Notes |
|----------|-------|-------|
| `NVIDIA_API_KEY` | `nvapi-xxxx` | Your NVIDIA NIM API key |
| `SECRET_KEY` | Auto-generate | Click "Generate" |
| `JWT_SECRET` | Auto-generate | Click "Generate" |
| `FLASK_ENV` | `production` | |
| `PORT` | `10000` | Default Render port |
| `UPLOAD_FOLDER` | `uploads` | |
| `EXPORT_FOLDER` | `exports` | |

#### 3. Deploy
- Click **"Create Web Service"**
- Wait 5-10 minutes for deployment
- Copy the backend URL: `https://bill-matcher-backend.onrender.com`

---

### Part 2: Deploy Frontend

#### 1. Update Frontend API URL
After backend is deployed, update `frontend/app.js` line 6:

```javascript
const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:5000/api'
    : 'https://YOUR-BACKEND-URL.onrender.com/api';  // Replace with your actual URL
```

Commit and push:
```bash
git add frontend/app.js
git commit -m "Update backend URL"
git push origin main
```

#### 2. Create Static Site
1. Click **"New +"** → **"Static Site"**
2. Connect same repository
3. Configure:
   - **Name:** `bill-matcher-frontend`
   - **Branch:** `main`
   - **Root Directory:** `frontend`
   - **Build Command:** (leave empty)
   - **Publish Directory:** `.`

#### 3. Deploy
- Click **"Create Static Site"**
- Copy the frontend URL: `https://bill-matcher-frontend.onrender.com`

---

### Part 3: Update CORS

#### Update Backend CORS with Frontend URL
In `backend/app.py`, the CORS is already configured, but verify the frontend URL matches:

```python
cors_origins = [
    'http://localhost:8080',
    'http://127.0.0.1:8080',
    'https://bill-matcher-frontend.onrender.com',  # Your actual frontend URL
]
```

Or add it as environment variable:
- Variable: `FRONTEND_URL`
- Value: `https://bill-matcher-frontend.onrender.com`

---

## Testing Deployment

1. Visit your frontend URL: `https://bill-matcher-frontend.onrender.com`
2. Test login (default: admin/admin123)
3. Upload sample bills
4. Verify matching works
5. Test on mobile device

---

## Important Notes

### Free Tier Limitations
- **Backend sleeps after 15 min of inactivity**
  - First request after sleep takes 30-60 seconds
  - Solution: Use uptime monitoring (see below)
- **750 free hours/month** (enough for 1 service 24/7)
- **No persistent storage** - uploaded files lost on restart

### Keep Backend Awake (Optional)
Use **UptimeRobot** or **Cron-job.org**:
- URL to ping: `https://YOUR-BACKEND-URL.onrender.com/api/health`
- Frequency: Every 10 minutes

### Persistent Storage (Recommended for Production)
Current setup loses files on restart. Solutions:
1. **Cloudinary** - Free image/file storage
2. **AWS S3** - Pay-as-you-go storage
3. **Render Disk** - $1/GB/month persistent disk

---

## Troubleshooting

### Backend won't start
- Check logs in Render dashboard
- Verify all environment variables are set
- Ensure `requirements.txt` has all dependencies
- Test locally first: `cd backend && python app.py`

### Frontend can't connect to backend
- Check browser console for errors
- Verify API_BASE_URL in `app.js` is correct
- Check backend CORS allows frontend domain
- Test backend health: `https://YOUR-BACKEND-URL.onrender.com/api/health`

### CORS errors
- Verify frontend URL is in backend CORS list
- Clear browser cache
- Check browser console for exact error

### Files not uploading
- Check file size (max 16MB)
- Verify NVIDIA_API_KEY is set correctly
- Check backend logs for errors

---

## Upgrade Options

### Paid Plans (Starting at $7/month)
- ✅ No sleep time
- ✅ Custom domains
- ✅ More CPU/RAM
- ✅ Priority support
- ✅ Persistent disk storage

---

## Post-Deployment Checklist

- [ ] Backend deployed and accessible
- [ ] Frontend deployed and accessible
- [ ] CORS configured correctly
- [ ] Environment variables set
- [ ] Health check working
- [ ] Login works
- [ ] File upload works
- [ ] Matching works
- [ ] Excel export works
- [ ] Tested on mobile device
- [ ] Set up uptime monitoring (optional)
- [ ] Add custom domain (optional)

---

## URLs to Update

After deployment, update these URLs in your code:

**In `frontend/app.js`:**
```javascript
: 'https://YOUR-ACTUAL-BACKEND-URL.onrender.com/api';
```

**In `backend/app.py`:**
```python
'https://YOUR-ACTUAL-FRONTEND-URL.onrender.com',
```

---

## Support

- Render Docs: https://render.com/docs
- Community: https://community.render.com
- Status: https://status.render.com

---

**Deployment Date:** [Add date after deploying]
**Backend URL:** [Add after deploying]
**Frontend URL:** [Add after deploying]
