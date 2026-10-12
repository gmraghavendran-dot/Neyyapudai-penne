import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
export default function Map({ incidents = [], center = [13.0827,80.2707] }) {
  return <div className="map"><MapContainer center={center} zoom={11} scrollWheelZoom><TileLayer attribution='&copy; OpenStreetMap' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"/>{incidents.map(i=><CircleMarker key={i.incident_id} center={[i.latitude,i.longitude]} radius={8} pathOptions={{color:"#ff4d5a",fillColor:"#ff4d5a",fillOpacity:.75}}><Popup>#{i.incident_id} · {i.incident_type}<br/>{i.location_label || "Unknown"}</Popup></CircleMarker>)}</MapContainer></div>;
}
