export default function Sidebar({ items = [], active, onChange }) {
  return <aside>{items.map(item => <button key={item.id} className={active === item.id ? "nav active" : "nav"} onClick={() => onChange(item.id)}>{item.label}</button>)}</aside>;
}
