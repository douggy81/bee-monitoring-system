import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card.jsx'
import { Button } from '@/components/ui/button.jsx'
import { Badge } from '@/components/ui/badge.jsx'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert.jsx'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs.jsx'
import { Progress } from '@/components/ui/progress.jsx'
import { 
  Activity, 
  Camera, 
  Heart, 
  AlertTriangle, 
  TrendingUp, 
  Battery, 
  Wifi,
  Eye,
  Bug,
  Thermometer,
  Droplets,
  Sun,
  Users,
  BarChart3,
  Settings
} from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts'
import './App.css'

// Mock data for demonstration
const mockActivityData = [
  { time: '06:00', beeCount: 12, activity: 45 },
  { time: '08:00', beeCount: 28, activity: 78 },
  { time: '10:00', beeCount: 35, activity: 92 },
  { time: '12:00', beeCount: 42, activity: 85 },
  { time: '14:00', beeCount: 38, activity: 88 },
  { time: '16:00', beeCount: 31, activity: 76 },
  { time: '18:00', beeCount: 19, activity: 54 },
]

const mockHealthData = [
  { date: '2025-09-15', health: 0.92, mites: 0.05, activity: 0.88 },
  { date: '2025-09-16', health: 0.89, mites: 0.08, activity: 0.85 },
  { date: '2025-09-17', health: 0.91, mites: 0.06, activity: 0.90 },
  { date: '2025-09-18', health: 0.87, mites: 0.12, activity: 0.82 },
  { date: '2025-09-19', health: 0.94, mites: 0.04, activity: 0.93 },
]

function App() {
  const [currentData, setCurrentData] = useState({
    beeCount: 34,
    behavior: 'foraging',
    healthScore: 0.89,
    temperature: 24.5,
    humidity: 62,
    lightLevel: 850,
    batteryLevel: 87,
    isOnline: true,
    lastUpdate: new Date().toLocaleTimeString()
  })

  const [alerts, setAlerts] = useState([
    {
      id: 1,
      level: 'warning',
      type: 'behavior',
      message: 'Increased agitation detected in colony',
      timestamp: '2025-09-19 14:30'
    },
    {
      id: 2,
      level: 'info',
      type: 'activity',
      message: 'Peak foraging activity observed',
      timestamp: '2025-09-19 12:15'
    }
  ])

  // Simulate real-time updates
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentData(prev => ({
        ...prev,
        beeCount: Math.max(5, prev.beeCount + Math.floor(Math.random() * 6 - 3)),
        temperature: 24.5 + Math.random() * 2 - 1,
        humidity: 62 + Math.random() * 4 - 2,
        lightLevel: 850 + Math.random() * 200 - 100,
        batteryLevel: Math.max(0, Math.min(100, prev.batteryLevel + Math.random() * 2 - 1)),
        lastUpdate: new Date().toLocaleTimeString()
      }))
    }, 5000)

    return () => clearInterval(interval)
  }, [])

  const getHealthColor = (score) => {
    if (score >= 0.8) return 'text-green-600'
    if (score >= 0.6) return 'text-yellow-600'
    return 'text-red-600'
  }

  const getBehaviorBadge = (behavior) => {
    const variants = {
      'foraging': 'default',
      'guarding': 'secondary',
      'swarming_prep': 'destructive',
      'agitated': 'destructive',
      'normal': 'outline'
    }
    return variants[behavior] || 'outline'
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-green-50 dark:from-gray-900 dark:to-gray-800">
      {/* Header */}
      <header className="bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm border-b border-gray-200 dark:border-gray-700 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-gradient-to-r from-yellow-400 to-orange-500 rounded-full flex items-center justify-center">
                <Bug className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900 dark:text-white">Digital4.ai</h1>
                <p className="text-sm text-gray-500 dark:text-gray-400">Bee Monitoring System</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <Wifi className={`w-4 h-4 ${currentData.isOnline ? 'text-green-500' : 'text-red-500'}`} />
                <span className="text-sm text-gray-600 dark:text-gray-300">
                  {currentData.isOnline ? 'Online' : 'Offline'}
                </span>
              </div>
              <div className="flex items-center space-x-2">
                <Battery className="w-4 h-4 text-gray-600 dark:text-gray-300" />
                <span className="text-sm text-gray-600 dark:text-gray-300">
                  {currentData.batteryLevel}%
                </span>
              </div>
              <Button variant="outline" size="sm">
                <Settings className="w-4 h-4 mr-2" />
                Settings
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Alerts */}
        {alerts.length > 0 && (
          <div className="mb-6 space-y-2">
            {alerts.map(alert => (
              <Alert key={alert.id} className={alert.level === 'warning' ? 'border-yellow-500' : 'border-blue-500'}>
                <AlertTriangle className="h-4 w-4" />
                <AlertTitle className="capitalize">{alert.level}</AlertTitle>
                <AlertDescription>
                  {alert.message} - {alert.timestamp}
                </AlertDescription>
              </Alert>
            ))}
          </div>
        )}

        {/* Key Metrics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card className="bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Active Bees</CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{currentData.beeCount}</div>
              <p className="text-xs text-muted-foreground">
                Last updated: {currentData.lastUpdate}
              </p>
            </CardContent>
          </Card>

          <Card className="bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Behavior</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="flex items-center space-x-2">
                <Badge variant={getBehaviorBadge(currentData.behavior)} className="capitalize">
                  {currentData.behavior.replace('_', ' ')}
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                AI-powered classification
              </p>
            </CardContent>
          </Card>

          <Card className="bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Health Score</CardTitle>
              <Heart className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold ${getHealthColor(currentData.healthScore)}`}>
                {(currentData.healthScore * 100).toFixed(0)}%
              </div>
              <Progress value={currentData.healthScore * 100} className="mt-2" />
            </CardContent>
          </Card>

          <Card className="bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Environment</CardTitle>
              <Thermometer className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="space-y-1">
                <div className="flex items-center justify-between text-sm">
                  <span>Temperature</span>
                  <span>{currentData.temperature.toFixed(1)}°C</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span>Humidity</span>
                  <span>{currentData.humidity.toFixed(0)}%</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span>Light</span>
                  <span>{currentData.lightLevel.toFixed(0)} lux</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Main Dashboard Tabs */}
        <Tabs defaultValue="activity" className="space-y-6">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="activity">Activity</TabsTrigger>
            <TabsTrigger value="health">Health</TabsTrigger>
            <TabsTrigger value="analytics">Analytics</TabsTrigger>
            <TabsTrigger value="camera">Camera</TabsTrigger>
          </TabsList>

          <TabsContent value="activity" className="space-y-6">
            <Card className="bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm">
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <BarChart3 className="w-5 h-5" />
                  <span>Daily Activity Pattern</span>
                </CardTitle>
                <CardDescription>
                  Bee count and activity levels throughout the day
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={mockActivityData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="time" />
                      <YAxis yAxisId="left" />
                      <YAxis yAxisId="right" orientation="right" />
                      <Tooltip />
                      <Line 
                        yAxisId="left"
                        type="monotone" 
                        dataKey="beeCount" 
                        stroke="#f59e0b" 
                        strokeWidth={2}
                        name="Bee Count"
                      />
                      <Line 
                        yAxisId="right"
                        type="monotone" 
                        dataKey="activity" 
                        stroke="#10b981" 
                        strokeWidth={2}
                        name="Activity Level"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card className="bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm">
                <CardHeader>
                  <CardTitle>Traffic Analysis</CardTitle>
                  <CardDescription>Entrance and exit activity</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">Entrances</span>
                      <span className="text-2xl font-bold text-green-600">142</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">Exits</span>
                      <span className="text-2xl font-bold text-blue-600">138</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">Net Activity</span>
                      <span className="text-2xl font-bold text-orange-600">+4</span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm">
                <CardHeader>
                  <CardTitle>Behavioral Indicators</CardTitle>
                  <CardDescription>Current colony behavior analysis</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">Foraging Activity</span>
                      <div className="flex items-center space-x-2">
                        <Progress value={78} className="w-20" />
                        <span className="text-sm">78%</span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">Guard Activity</span>
                      <div className="flex items-center space-x-2">
                        <Progress value={45} className="w-20" />
                        <span className="text-sm">45%</span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">Swarming Risk</span>
                      <div className="flex items-center space-x-2">
                        <Progress value={12} className="w-20" />
                        <span className="text-sm">12%</span>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="health" className="space-y-6">
            <Card className="bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm">
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Heart className="w-5 h-5" />
                  <span>Health Trend Analysis</span>
                </CardTitle>
                <CardDescription>
                  Colony health metrics over the past week
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={mockHealthData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="date" />
                      <YAxis />
                      <Tooltip />
                      <Area 
                        type="monotone" 
                        dataKey="health" 
                        stackId="1"
                        stroke="#10b981" 
                        fill="#10b981"
                        fillOpacity={0.6}
                        name="Overall Health"
                      />
                      <Area 
                        type="monotone" 
                        dataKey="activity" 
                        stackId="2"
                        stroke="#3b82f6" 
                        fill="#3b82f6"
                        fillOpacity={0.6}
                        name="Activity Score"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <Card className="bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm">
                <CardHeader>
                  <CardTitle>Mite Detection</CardTitle>
                  <CardDescription>AI-powered mite analysis</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="text-center">
                    <div className="text-3xl font-bold text-green-600">2.1%</div>
                    <p className="text-sm text-muted-foreground">Mite presence detected</p>
                    <Badge variant="outline" className="mt-2">Within normal range</Badge>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm">
                <CardHeader>
                  <CardTitle>Wing Condition</CardTitle>
                  <CardDescription>Physical health assessment</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="text-center">
                    <div className="text-3xl font-bold text-green-600">94%</div>
                    <p className="text-sm text-muted-foreground">Healthy wings detected</p>
                    <Badge variant="default" className="mt-2">Excellent</Badge>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm">
                <CardHeader>
                  <CardTitle>Population Health</CardTitle>
                  <CardDescription>Colony size and distribution</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="text-center">
                    <div className="text-3xl font-bold text-blue-600">89%</div>
                    <p className="text-sm text-muted-foreground">Population stability</p>
                    <Badge variant="secondary" className="mt-2">Stable</Badge>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="analytics" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card className="bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm">
                <CardHeader>
                  <CardTitle>Predictive Analytics</CardTitle>
                  <CardDescription>AI-powered predictions and insights</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                      <h4 className="font-medium text-blue-900 dark:text-blue-100">Weather Impact</h4>
                      <p className="text-sm text-blue-700 dark:text-blue-300">
                        Sunny weather tomorrow will likely increase foraging activity by 25%
                      </p>
                    </div>
                    <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
                      <h4 className="font-medium text-green-900 dark:text-green-100">Health Forecast</h4>
                      <p className="text-sm text-green-700 dark:text-green-300">
                        Colony health expected to remain stable over the next week
                      </p>
                    </div>
                    <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
                      <h4 className="font-medium text-yellow-900 dark:text-yellow-100">Activity Pattern</h4>
                      <p className="text-sm text-yellow-700 dark:text-yellow-300">
                        Peak activity window shifting earlier due to seasonal changes
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm">
                <CardHeader>
                  <CardTitle>System Performance</CardTitle>
                  <CardDescription>AI model and hardware metrics</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">Detection Accuracy</span>
                      <div className="flex items-center space-x-2">
                        <Progress value={96} className="w-20" />
                        <span className="text-sm">96%</span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">Processing Speed</span>
                      <div className="flex items-center space-x-2">
                        <Progress value={89} className="w-20" />
                        <span className="text-sm">89 FPS</span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">AI HAT+ Utilization</span>
                      <div className="flex items-center space-x-2">
                        <Progress value={73} className="w-20" />
                        <span className="text-sm">73%</span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">Storage Used</span>
                      <div className="flex items-center space-x-2">
                        <Progress value={34} className="w-20" />
                        <span className="text-sm">87GB</span>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="camera" className="space-y-6">
            <Card className="bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm">
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Camera className="w-5 h-5" />
                  <span>Live Camera Feed</span>
                </CardTitle>
                <CardDescription>
                  Real-time view from Camera Module 3 with AI detection overlay
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="relative bg-gray-900 rounded-lg overflow-hidden aspect-video">
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="text-center text-white">
                      <Camera className="w-16 h-16 mx-auto mb-4 opacity-50" />
                      <p className="text-lg font-medium">Camera Feed</p>
                      <p className="text-sm opacity-75">Live video stream would appear here</p>
                      <div className="mt-4 flex items-center justify-center space-x-4">
                        <Badge variant="secondary">1920x1080</Badge>
                        <Badge variant="secondary">30 FPS</Badge>
                        <Badge variant="secondary">AI Detection: ON</Badge>
                      </div>
                    </div>
                  </div>
                  {/* Simulated detection boxes */}
                  <div className="absolute top-4 left-4 w-8 h-8 border-2 border-yellow-400 rounded"></div>
                  <div className="absolute top-12 right-8 w-6 h-6 border-2 border-yellow-400 rounded"></div>
                  <div className="absolute bottom-8 left-12 w-7 h-7 border-2 border-yellow-400 rounded"></div>
                </div>
                <div className="mt-4 flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <Button variant="outline" size="sm">
                      <Eye className="w-4 h-4 mr-2" />
                      View Full Screen
                    </Button>
                    <Button variant="outline" size="sm">
                      Record
                    </Button>
                  </div>
                  <div className="text-sm text-muted-foreground">
                    Last frame: {currentData.lastUpdate}
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  )
}

export default App
