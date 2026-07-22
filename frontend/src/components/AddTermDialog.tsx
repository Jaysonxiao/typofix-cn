import type { TermLibrary } from "../types";

export function AddTermDialog({ term, libraries, selected, onChange, onConfirm, onCancel }: { term: string; libraries: TermLibrary[]; selected: string; onChange: (value: string) => void; onConfirm: () => void; onCancel: () => void }) {
  return <div className="term-dialog" role="dialog" aria-label="添加术语"><div><p className="eyebrow">术语校注</p><h3>把“{term}”加入术语库</h3><label>目标术语库<select aria-label="目标术语库" value={selected} onChange={(event) => onChange(event.target.value)}>{libraries.map((library) => <option key={library.name} value={library.name}>{library.name}</option>)}</select></label><div className="dialog-actions"><button onClick={onCancel}>取消</button><button className="primary-button" onClick={onConfirm} disabled={!selected}>确认添加</button></div></div></div>;
}
