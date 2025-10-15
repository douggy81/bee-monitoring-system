# 🚀 Bee Monitoring System - Deployment & Data Collection Strategy

**Goal:** Get the system deployed and collecting real bee data for product finalization

---

## 🏗️ Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PUBLIC INTERNET                           │
└───────────────────┬─────────────────────────────────────────┘
                    │
    ┌───────────────┴───────────────┐
    │                               │
    ▼                               ▼
┌──────────────────┐        ┌──────────────────┐
│ Dashboard        │        │ Data Storage     │
│ (Vercel/Netlify) │◄───────┤ (Supabase)       │
│ digital4.ai      │        │ PostgreSQL +     │
│ bee.digital4.ai  │        │ File Storage     │
└──────────────────┘        └──────────────────┘
                                    ▲
                                    │
                            ┌───────┴────────┐
                            │                │
                    ┌───────┴──────┐  ┌──────┴────────┐
                    │ Pi #1        │  │ Pi #2         │
                    │ (Your hive)  │  │ (Future)      │
                    │ 192.168.x.x  │  │ Location TBD  │
                    └──────────────┘  └───────────────┘
```

---

## 📍 Phase 1: Single-Hive Deployment (Current)

### **Option A: Cloud-Connected Pi (Recommended)**

**Setup:**
1. **Raspberry Pi** → Processes video locally
2. **API** → Exposes data endpoint
3. **Webhook/Cron** → Pushes data to Supabase every minute
4. **Dashboard** → Reads from Supabase (fast, always available)

**Pros:**
- ✅ Pi stays local (no public exposure)
- ✅ Dashboard works even if Pi offline
- ✅ Historical data preserved
- ✅ Scalable to multiple hives

**Cons:**
- ⚠️ Requires stable internet at hive location
- ⚠️ Small monthly cost (~$0-25/month for Supabase)

---

### **Option B: Direct Pi Access (Demo Only)**

**Setup:**
1. **Port Forward** → Expose Pi API to internet
2. **Dynamic DNS** → Give Pi a stable URL
3. **Dashboard** → Reads directly from Pi

**Pros:**
- ✅ Free
- ✅ No cloud service needed
- ✅ Real-time (no delay)

**Cons:**
- ❌ Security risk (Pi exposed)
- ❌ Dashboard fails if Pi offline
- ❌ No historical data backup
- ❌ Doesn't scale

---

## 🎯 Recommended: Option A with Supabase

### Step 1: Setup Supabase (5 minutes)

```bash
# 1. Create account: https://supabase.com (free tier)
# 2. Create new project: "bee-monitoring"
# 3. Get credentials (Settings → API)
```

### Step 2: Database Schema

```sql
-- Create bee_detections table
CREATE TABLE bee_detections (
  id BIGSERIAL PRIMARY KEY,
  timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  hive_id TEXT NOT NULL DEFAULT 'hive-01',
  bee_count INTEGER NOT NULL,
  behavior_flying INTEGER DEFAULT 0,
  behavior_erratic INTEGER DEFAULT 0,
  behavior_browsing INTEGER DEFAULT 0,
  avg_confidence FLOAT,
  temperature FLOAT,
  humidity FLOAT,
  metadata JSONB
);

-- Create index for fast queries
CREATE INDEX idx_detections_timestamp ON bee_detections(timestamp DESC);
CREATE INDEX idx_detections_hive ON bee_detections(hive_id, timestamp DESC);

-- Create video_snapshots table (for storing processed videos)
CREATE TABLE video_snapshots (
  id BIGSERIAL PRIMARY KEY,
  timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  hive_id TEXT NOT NULL,
  video_url TEXT NOT NULL,
  duration_seconds FLOAT,
  total_bees INTEGER,
  behaviors JSONB,
  metadata JSONB
);
```

### Step 3: Pi → Supabase Integration

Add to your Pi `/opt/bee-monitoring/src/api/data_sync.py`:

```python
#!/usr/bin/env python3
"""
Sync bee monitoring data to Supabase
Run every minute via cron
"""

import os
import json
import requests
from datetime import datetime
from supabase import create_client, Client

# Supabase credentials (from environment or config)
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://your-project.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', 'your-anon-key')

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_current_bee_stats():
    """Fetch current stats from local API"""
    try:
        response = requests.get('http://localhost:8000/api/detection/latest', timeout=5)
        return response.json()
    except Exception as e:
        print(f"Error fetching stats: {e}")
        return None

def sync_to_supabase():
    """Push current data to Supabase"""
    stats = get_current_bee_stats()
    
    if not stats:
        return
    
    # Prepare data
    data = {
        'hive_id': 'hive-01',  # Your hive identifier
        'bee_count': stats.get('bee_count', 0),
        'behavior_flying': stats.get('behaviors', {}).get('flying', 0),
        'behavior_erratic': stats.get('behaviors', {}).get('erratic', 0),
        'behavior_browsing': stats.get('behaviors', {}).get('browsing', 0),
        'avg_confidence': stats.get('avg_confidence', 0.0),
        'temperature': stats.get('temperature'),
        'humidity': stats.get('humidity'),
        'metadata': json.dumps(stats.get('metadata', {}))
    }
    
    try:
        result = supabase.table('bee_detections').insert(data).execute()
        print(f"✅ Synced to Supabase: {len(result.data)} records")
    except Exception as e:
        print(f"❌ Sync failed: {e}")

if __name__ == '__main__':
    sync_to_supabase()
```

**Setup cron on Pi:**
```bash
# Edit crontab
crontab -e

# Add line to run every minute
* * * * * cd /opt/bee-monitoring/src && /usr/bin/python3 api/data_sync.py >> /tmp/supabase_sync.log 2>&1
```

### Step 4: Dashboard → Supabase Connection

Update your React dashboard to fetch from Supabase:

```javascript
// dashboard/src/hooks/useSupabaseData.js
import { createClient } from '@supabase/supabase-js'
import { useEffect, useState } from 'react'

const supabase = createClient(
  process.env.VITE_SUPABASE_URL,
  process.env.VITE_SUPABASE_ANON_KEY
)

export function useBeeData(hiveId = 'hive-01', timeRange = '1 hour') {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchData() {
      const { data: records, error } = await supabase
        .from('bee_detections')
        .select('*')
        .eq('hive_id', hiveId)
        .gte('timestamp', new Date(Date.now() - 60*60*1000).toISOString()) // Last hour
        .order('timestamp', { ascending: false })
        .limit(1000)

      if (error) {
        console.error('Error fetching data:', error)
      } else {
        setData(records)
      }
      setLoading(false)
    }

    fetchData()
    
    // Realtime subscription
    const subscription = supabase
      .channel('bee_detections')
      .on('postgres_changes', 
        { event: 'INSERT', schema: 'public', table: 'bee_detections' },
        (payload) => {
          setData(prev => [payload.new, ...prev].slice(0, 1000))
        }
      )
      .subscribe()

    return () => {
      subscription.unsubscribe()
    }
  }, [hiveId, timeRange])

  return { data, loading }
}

// Usage in component:
// const { data, loading } = useBeeData('hive-01', '1 hour')
```

### Step 5: Deploy Dashboard

```bash
# Install Vercel CLI
npm install -g vercel

# Navigate to dashboard
cd dashboard

# Add environment variables
echo "VITE_SUPABASE_URL=https://your-project.supabase.co" > .env
echo "VITE_SUPABASE_ANON_KEY=your-anon-key" >> .env

# Deploy
vercel --prod

# Custom domain (optional)
# bee.digital4.ai → Point to Vercel deployment
```

---

## 📊 Data Collection Strategy

### **Metrics to Collect:**

1. **Real-time (every minute):**
   - Current bee count
   - Behavior breakdown (flying/erratic/browsing)
   - Average confidence
   - Temperature/humidity (if sensors added)

2. **Hourly summaries:**
   - Peak activity time
   - Total unique bees (estimated)
   - Behavior patterns
   - Anomaly detection

3. **Daily summaries:**
   - Activity heatmap
   - Health trends
   - Weather correlation
   - Long-term patterns

4. **Video snapshots (every 10 minutes):**
   - 30-second clip processed with ByteTrack
   - Stored in Supabase Storage
   - URL saved to database
   - Viewable in dashboard

---

## 🎯 Next Steps for Product Finalization:

### Week 1: Setup Infrastructure
- [x] Create Supabase project
- [ ] Deploy database schema
- [ ] Configure Pi data sync
- [ ] Test data flow

### Week 2: Dashboard Enhancements
- [ ] Connect dashboard to Supabase
- [ ] Add real-time charts
- [ ] Implement behavior visualizations
- [ ] Add video playback gallery

### Week 3: Data Collection
- [ ] Run system 24/7 for 1 week
- [ ] Collect baseline data
- [ ] Identify patterns
- [ ] Tune thresholds

### Week 4: Analysis & Refinement
- [ ] Analyze collected data
- [ ] Refine behavior algorithms
- [ ] Create insights dashboard
- [ ] Prepare demo

---

## 💰 Cost Estimate:

**Free Tier (Good for 1-3 hives):**
- Supabase: Free (500MB database, 1GB storage)
- Vercel: Free (hobby tier)
- **Total: $0/month**

**Scaled (10+ hives):**
- Supabase Pro: $25/month (8GB database, 100GB storage)
- Vercel Pro: $20/month (better performance)
- **Total: $45/month**

---

## 🔒 Security Considerations:

1. **Pi Security:**
   - No public exposure
   - One-way data push only
   - VPN optional for remote access

2. **Supabase:**
   - Row-level security enabled
   - API keys in environment variables
   - HTTPS only

3. **Dashboard:**
   - Read-only access for public
   - Admin panel password-protected
   - CORS configured

---

## 🚀 Ready to Deploy?

**I can help you with:**
1. Setting up Supabase
2. Writing the Pi sync script
3. Updating the dashboard
4. Deploying to Vercel
5. Monitoring data flow

**Which part do you want to start with?**
