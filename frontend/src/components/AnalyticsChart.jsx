import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";
export default function AnalyticsChart({ data = [], xKey = "label", yKey = "risk_score" }) {
  return <div style={{height:260}}><ResponsiveContainer><LineChart data={data}><CartesianGrid strokeDasharray="3 3" stroke="#233044"/><XAxis dataKey={xKey} stroke="#7f8ca0"/><YAxis stroke="#7f8ca0"/><Tooltip/><Line type="monotone" dataKey={yKey} stroke="#ff4d5a" strokeWidth={3} dot={false}/></LineChart></ResponsiveContainer></div>;
}
