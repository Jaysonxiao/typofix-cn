import { useEffect, useState } from "react";

import { addTerm, createTermLibrary, deleteTerm, listTermLibraries } from "../api/client";
import type { TermLibrary } from "../types";

export function TermsPage() {
  const [libraries, setLibraries] = useState<TermLibrary[]>([]);
  const [selected, setSelected] = useState("");
  const [newLibrary, setNewLibrary] = useState("");
  const [newTerm, setNewTerm] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { listTermLibraries().then((items) => { setLibraries(items); setSelected(items[0]?.name ?? ""); }).catch((reason: Error) => setError(reason.message)); }, []);

  async function create() {
    if (!newLibrary.trim()) return;
    try { const library = await createTermLibrary(newLibrary.trim()); setLibraries((items) => [...items, library]); setSelected(library.name); setNewLibrary(""); } catch (reason) { setError(reason instanceof Error ? reason.message : "术语库创建失败"); }
  }

  async function add() {
    if (!selected || !newTerm.trim()) return;
    try { const library = await addTerm(selected, newTerm.trim()); setLibraries((items) => items.map((item) => item.name === library.name ? library : item)); setNewTerm(""); } catch (reason) { setError(reason instanceof Error ? reason.message : "术语添加失败"); }
  }

  async function remove(term: string) {
    try { const library = await deleteTerm(selected, term); setLibraries((items) => items.map((item) => item.name === library.name ? library : item)); } catch (reason) { setError(reason instanceof Error ? reason.message : "术语删除失败"); }
  }

  const current = libraries.find((item) => item.name === selected);
  return <main className="terms-page"><header className="page-header"><div><p className="kicker">术语 / PLAIN TEXT</p><h1>让专业名词保持原样。</h1><p>每个术语库都是一个可直接编辑的 UTF-8 文本文件；这里的改动会立即影响后续匹配。</p></div><a className="back-link" href="/">返回校验 ↗</a></header>{error && <p className="error-copy" role="alert">{error}</p>}<section className="terms-layout"><aside className="terms-sidebar"><p className="eyebrow">术语库</p>{libraries.map((library) => <button className={library.name === selected ? "library-tab is-active" : "library-tab"} key={library.name} onClick={() => setSelected(library.name)}>{library.name}<span>{library.terms.length}</span></button>)}<div className="new-library"><label htmlFor="new-library">新术语库名称</label><input id="new-library" value={newLibrary} onChange={(event) => setNewLibrary(event.target.value)} placeholder="例如：论文" /><button onClick={create}>创建术语库</button></div></aside><section className="terms-card"><div className="section-heading"><div><p className="eyebrow">当前词表</p><h2>{current?.name ?? "尚未选择"}</h2></div><a className="text-link" href={current ? `/api/v1/term-libraries/${encodeURIComponent(current.name)}/download` : "#"}>下载 .txt ↗</a></div>{current ? <><div className="term-add-row"><input aria-label="新增术语" value={newTerm} onChange={(event) => setNewTerm(event.target.value)} placeholder="输入术语后添加" /><button className="primary-button" onClick={add} disabled={!newTerm.trim()}>添加术语</button></div><ul className="term-list">{current.terms.map((term) => <li key={term}><span>{term}</span><button aria-label={`删除${term}`} onClick={() => remove(term)}>移除</button></li>)}</ul>{!current.terms.length && <p className="empty-copy">还没有术语。可以从报告页划词添加，也可以在这里直接输入。</p>}</> : <p className="empty-copy">先创建一个术语库。</p>}</section></section></main>;
}
