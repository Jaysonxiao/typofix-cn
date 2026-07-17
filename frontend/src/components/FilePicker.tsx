import type { InputHTMLAttributes } from "react";

interface FilePickerProps {
  files: File[];
  onChange: (files: File[]) => void;
}

export function FilePicker({ files, onChange }: FilePickerProps) {
  const normalize = (selected: FileList | null) => {
    const docx = Array.from(selected ?? []).filter((file) => file.name.toLowerCase().endsWith(".docx") && !file.name.startsWith("~$"));
    onChange(docx);
  };

  return (
    <div className="picker-grid">
      <label className="picker-card">
        <span className="eyebrow">文档入口</span>
        <strong>上传文件</strong>
        <small>选择一个或多个 DOCX</small>
        <input aria-label="上传文件" type="file" accept=".docx" multiple onChange={(event) => normalize(event.target.files)} />
      </label>
      <label className="picker-card picker-card-muted">
        <span className="eyebrow">批量入口</span>
        <strong>上传文件夹</strong>
        <small>递归收集 DOCX 文档</small>
        <input aria-label="上传文件夹" type="file" accept=".docx" multiple onChange={(event) => normalize(event.target.files)} {...({ webkitdirectory: "" } as InputHTMLAttributes<HTMLInputElement>)} />
      </label>
      {files.length > 0 && <p className="picker-count">已选择 {files.length} 个 DOCX</p>}
    </div>
  );
}
