# 🐝 Bee Hive Health Metrics Design

## 📹 **Detection Video Overlays (5-second rolling average)**

### **Metrics Displayed:**
```
┌─────────────────────────────────────────┐
│ 🐝 Bee Activity (5s avg)               │
│ ─────────────────────────────────       │
│ Total Bees:        32.4                │
│ Entering:          8.2  (↑ foraging)   │
│ Exiting:           6.8  (↓ returning)  │
│ Net Flow:         +1.4  (population ↑) │
│ Activity Level:    HIGH                │
└─────────────────────────────────────────┘
```

### **Metadata Output:**
```json
{
  "rolling_averages_5sec": [
    {
      "timestamp": 5.0,
      "window_start": 0.0,
      "window_end": 5.0,
      "avg_total_bees": 32.4,
      "avg_bees_entering": 8.2,
      "avg_bees_exiting": 6.8,
      "net_flow": 1.4,
      "activity_level": "HIGH"
    },
    ...
  ]
}
```

---

## 🎯 **ByteTrack Health Metrics**

### **1. Traffic Analysis**
**Purpose:** Measure hive activity and foraging patterns

**Metrics:**
- **Entrance Rate** (bees/min) - New tracks appearing on entrance side
- **Exit Rate** (bees/min) - Tracks disappearing on entrance side  
- **Net Traffic** - Entrance - Exit (population change)
- **Traffic Density** - Active tracks / frame area
- **Peak Activity Times** - Time windows with highest traffic

**Health Indicators:**
- ✅ **Healthy:** Balanced entrance/exit, steady traffic
- ⚠️ **Warning:** Imbalanced traffic, sudden drops
- 🚨 **Critical:** No traffic, all exiting

---

### **2. Movement Patterns**
**Purpose:** Detect stress, swarming, or illness

**Metrics:**
- **Average Speed** (px/sec) - Normal foraging vs agitated
- **Speed Variance** - Consistent vs erratic movement
- **Directional Coherence** - Organized vs chaotic
- **Clustering Index** - Grouped vs dispersed
- **Dwell Time** - How long bees stay in frame

**Health Indicators:**
- ✅ **Healthy:** Moderate speed, low variance, organized movement
- ⚠️ **Warning:** High variance, clustering at entrance
- 🚨 **Critical:** Very high speed (panic), no movement (lethargy)

---

### **3. Population Dynamics**
**Purpose:** Track hive population and stability

**Metrics:**
- **Unique Bees (24h)** - Total different tracks
- **Long-Term Residents** - Tracks > 1 minute (house bees)
- **Short Visits** - Tracks < 10 sec (foragers)
- **Average Track Length** - Engagement time
- **Track Completeness** - % tracks with clear enter/exit

**Health Indicators:**
- ✅ **Healthy:** Mix of long/short tracks, high completeness
- ⚠️ **Warning:** Only short tracks (no house bees)
- 🚨 **Critical:** Very few unique tracks (population loss)

---

### **4. Foraging Efficiency**
**Purpose:** Estimate pollen/nectar collection (proxy)**

**Metrics:**
- **Foraging Ratio** - Exiting / Entering bees
- **Return Speed** - Average speed of entering bees (loaded = slower)
- **Trip Duration** - Time between exit and re-entry
- **Foraging Success Rate** - % bees that return
- **Daily Foraging Patterns** - Peak times, weather correlation

**Health Indicators:**
- ✅ **Healthy:** High return rate, slower entry speed (loaded)
- ⚠️ **Warning:** Low return rate, fast entry (empty)
- 🚨 **Critical:** No returns (lost bees, CCD)

---

### **5. Behavioral Anomalies**
**Purpose:** Early warning system for problems

**Metrics:**
- **Swarming Score** - Mass exit + clustering
- **Guarding Activity** - Bees hovering at entrance
- **Drift/Disorientation** - Erratic paths, collisions
- **Aggression Index** - Fast, direct movements
- **Robbing Detection** - Abnormal entrance attempts

**Health Indicators:**
- ✅ **Healthy:** Normal patterns, low anomaly score
- ⚠️ **Warning:** Occasional anomalies
- 🚨 **Critical:** Sustained anomalies (swarm, robbing)

---

### **6. Time-Series Health Score**
**Purpose:** Overall hive health (0-100)**

**Components:**
- Traffic Balance (20%) - Balanced entrance/exit
- Movement Quality (20%) - Organized, moderate speed
- Population Stability (20%) - Consistent unique tracks
- Foraging Efficiency (20%) - High return rate
- Anomaly Score (20%) - Low abnormal behavior

**Calculation:**
```python
health_score = (
    traffic_balance_score * 0.2 +
    movement_quality_score * 0.2 +
    population_stability_score * 0.2 +
    foraging_efficiency_score * 0.2 +
    (100 - anomaly_score) * 0.2
)
```

**Health Status:**
- 🟢 **90-100:** Excellent - Thriving hive
- 🟡 **70-89:** Good - Normal activity
- 🟠 **50-69:** Warning - Monitor closely
- 🔴 **0-49:** Critical - Intervention needed

---

## 📊 **Metadata Structure**

### **Detection Video Metadata:**
```json
{
  "video_metadata": { ... },
  "detection_summary": {
    "total_detections": 45231,
    "avg_bees_per_frame": 32.4,
    "max_bees_single_frame": 58,
    "min_bees_single_frame": 12
  },
  "rolling_averages_5sec": [
    {
      "timestamp": 5.0,
      "avg_total_bees": 32.4,
      "avg_entering": 8.2,
      "avg_exiting": 6.8,
      "net_flow": 1.4,
      "activity_level": "HIGH"
    },
    ...
  ],
  "per_frame_data": [ ... ]
}
```

### **ByteTrack Metadata:**
```json
{
  "video_metadata": { ... },
  "detection_summary": { ... },
  "health_metrics": {
    "traffic_analysis": {
      "entrance_rate_per_min": 24.5,
      "exit_rate_per_min": 22.3,
      "net_traffic_per_min": 2.2,
      "traffic_density": 0.042,
      "peak_activity_time": "14:23:00"
    },
    "movement_patterns": {
      "avg_speed_px_per_sec": 15.7,
      "speed_variance": 8.3,
      "directional_coherence": 0.72,
      "clustering_index": 0.35,
      "avg_dwell_time_sec": 3.4
    },
    "population_dynamics": {
      "unique_tracks": 127,
      "long_term_residents": 23,
      "short_visits": 89,
      "avg_track_length_frames": 45.2,
      "track_completeness": 0.68
    },
    "foraging_efficiency": {
      "foraging_ratio": 1.10,
      "avg_return_speed_px_per_sec": 12.3,
      "avg_trip_duration_sec": 180.5,
      "foraging_success_rate": 0.85
    },
    "behavioral_anomalies": {
      "swarming_score": 0.12,
      "guarding_activity": 0.08,
      "disorientation_score": 0.05,
      "aggression_index": 0.03,
      "anomaly_total": 0.28
    },
    "overall_health": {
      "score": 82.5,
      "status": "GOOD",
      "traffic_balance": 88,
      "movement_quality": 85,
      "population_stability": 80,
      "foraging_efficiency": 78,
      "anomaly_penalty": 28
    }
  },
  "time_series_health": [
    {
      "timestamp": 10.0,
      "health_score": 82.5,
      "status": "GOOD"
    },
    ...
  ],
  "tracking_metrics": { ... },
  "per_frame_data": [ ... ]
}
```

---

## 🎨 **Video Overlay Design**

### **Detection Video Overlay:**
```
┌──────────────────────────────────────┐
│ Frame: 450 | Time: 15.0s            │
│                                      │
│ 🐝 Rolling Avg (5s):                │
│   Total:       32.4                  │
│   Entering:     8.2 ↑               │
│   Exiting:      6.8 ↓               │
│   Net Flow:    +1.4 ⬆               │
│   Activity:    HIGH 🟢              │
└──────────────────────────────────────┘
```

### **ByteTrack Video Overlay:**
```
┌──────────────────────────────────────┐
│ Frame: 450 | Time: 15.0s            │
│                                      │
│ 🎯 Tracking Stats:                  │
│   Active:      28 tracks            │
│   New:         +3                    │
│   Lost:        -1                    │
│   Total IDs:   127                   │
│                                      │
│ 💚 Health Score: 82.5 (GOOD)        │
│   Traffic:     88% ✅               │
│   Movement:    85% ✅               │
│   Population:  80% ✅               │
│   Foraging:    78% ⚠️               │
└──────────────────────────────────────┘
```

---

## 🚀 **Implementation Priority**

### **Phase 1: Basic Metrics** (Now)
- ✅ Rolling 5-sec averages for detection
- ✅ Entrance/exit counting (basic)
- ✅ ByteTrack with basic stats

### **Phase 2: Health Scoring** (Next)
- ⏳ Traffic analysis
- ⏳ Movement patterns
- ⏳ Overall health score

### **Phase 3: Advanced Analytics** (Future)
- 🔲 Foraging efficiency
- 🔲 Behavioral anomalies
- 🔲 Predictive alerts

### **Phase 4: Pollen Detection** (Future)
- 🔲 Retrain model with "bee_with_pollen" class
- 🔲 Color analysis (pollen baskets)
- 🔲 Direct foraging metrics

---

## 📈 **Dashboard Integration**

### **Real-Time Widgets:**
1. **Activity Gauge** - Current bee count
2. **Traffic Graph** - Entrance/exit over time
3. **Health Score** - 0-100 with color coding
4. **Alert Panel** - Anomaly warnings

### **Historical Charts:**
1. **Population Trend** - Unique tracks over days
2. **Foraging Pattern** - Daily activity heatmap
3. **Health Timeline** - Score history
4. **Weather Correlation** - Activity vs temperature

---

## ✅ **Immediate Action**

Creating enhanced scripts with:

**Detection Video:**
- 5-second rolling averages
- Entrance/exit estimation (position-based)
- Activity level classification
- Enhanced overlay

**ByteTrack Video:**
- All tracking metrics
- Health score calculation
- Time-series analysis
- Comprehensive overlay

**Metadata:**
- All metrics exported to JSON
- Dashboard-ready format
- Time-series data included
