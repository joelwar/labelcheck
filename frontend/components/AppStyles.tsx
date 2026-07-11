export function AppStyles() {
  return (
    <style>{`
      .lv-root {
        --ink: #1c2a24;
        --paper: #f6f4ee;
        --paper-line: #d9d4c6;
        --brass: #8a6d3b;
        --green: #2f6b4f;
        --amber: #a4720f;
        --red: #a3372f;
        --neutral: #5d635b;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        background: var(--paper);
        color: var(--ink);
        min-height: 100vh;
        padding: 32px 20px;
        box-sizing: border-box;
      }
      .lv-container { max-width: 760px; margin: 0 auto; }
      .lv-container.wide { max-width: 980px; }
      .lv-header { margin-bottom: 24px; border-bottom: 2px solid var(--ink); padding-bottom: 16px; }
      .lv-eyebrow { font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase; color: var(--brass); font-weight: 700; margin-bottom: 6px; }
      .lv-title { font-size: 24px; font-weight: 700; margin: 0 0 4px 0; letter-spacing: 0; }
      .lv-subtitle { font-size: 14px; color: #55584f; margin: 0; line-height: 1.45; }
      .lv-section-label { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: var(--brass); margin: 22px 0 10px 0; }
      .lv-section-label.flush { margin-top: 0; }
      .lv-toolbar { display: flex; justify-content: space-between; gap: 16px; align-items: center; margin-bottom: 16px; }
      .lv-panel { background: #fff; border: 1.5px solid var(--paper-line); border-radius: 8px; padding: 18px; margin-bottom: 18px; }
      .lv-form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-bottom: 14px; }
      .lv-field { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
      .lv-field span { font-size: 12px; font-weight: 700; color: #55584f; }
      .lv-input {
        width: 100%; box-sizing: border-box; border: 1.5px solid var(--paper-line);
        border-radius: 6px; padding: 10px 11px; font: inherit; color: var(--ink); background: #fff;
      }
      .lv-input:focus, .lv-reason:focus { outline: 2px solid #c9d9ce; outline-offset: 1px; border-color: var(--green); }
      .lv-mode-toggle, .lv-actions { display: flex; gap: 8px; margin-bottom: 14px; flex-wrap: wrap; }
      .lv-mode-btn {
        font-size: 13px; padding: 7px 12px; border-radius: 6px;
        border: 1.5px solid var(--paper-line); background: #fff; color: #55584f;
        cursor: pointer; font-family: inherit;
      }
      .lv-mode-btn.active { border-color: var(--green); color: var(--green); font-weight: 700; background: #eef4f0; }
      .lv-upload-row, .lv-doc-grid { display: flex; gap: 12px; margin-bottom: 8px; flex-wrap: wrap; }
      .lv-upload-slot {
        flex: 1 1 220px; display: flex; align-items: center; gap: 12px;
        border: 1.5px dashed var(--paper-line); border-radius: 8px; background: #fff;
        padding: 14px 16px; cursor: pointer; transition: border-color 0.15s ease;
        min-height: 74px; box-sizing: border-box;
      }
      .lv-upload-slot:hover { border-color: var(--brass); }
      .lv-upload-slot input { position: absolute; opacity: 0; pointer-events: none; }
      .lv-upload-icon { width: 34px; height: 34px; border-radius: 6px; background: #f0ede2; display: flex; align-items: center; justify-content: center; color: var(--brass); flex-shrink: 0; }
      .lv-upload-text { min-width: 0; }
      .lv-upload-label { font-size: 13.5px; font-weight: 700; }
      .lv-upload-hint { font-size: 12px; color: #8a8d82; margin-top: 2px; overflow-wrap: anywhere; line-height: 1.35; }
      .lv-upload-note { font-size: 12px; color: #8a8d82; margin: 10px 0 0 0; font-style: italic; line-height: 1.5; }
      .lv-run-btn {
        display: inline-flex; align-items: center; justify-content: center; gap: 8px;
        font-size: 14px; font-weight: 600; padding: 10px 18px; border-radius: 6px;
        border: none; background: var(--green); color: #fff; cursor: pointer;
        font-family: inherit; margin: 18px 0 0 0; min-height: 42px; text-decoration: none;
      }
      .lv-run-btn.small { margin: 0; }
      .lv-run-btn.secondary { background: var(--ink); }
      .lv-run-btn.danger { background: var(--red); }
      .lv-run-btn:disabled { cursor: not-allowed; background: #8a8d82; opacity: 0.8; }
      .lv-alert { display: flex; gap: 10px; align-items: flex-start; border: 1.5px solid #e0b4ae; background: #fff4f2; color: var(--red); padding: 12px 14px; border-radius: 8px; margin: 14px 0; font-size: 13.5px; line-height: 1.45; }
      .lv-summary { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 16px 18px; border-radius: 8px; margin-bottom: 20px; border: 1.5px solid var(--paper-line); background: #fff; }
      .lv-summary-text { font-size: 15px; font-weight: 700; margin: 0 0 2px 0; }
      .lv-summary-sub { font-size: 13px; color: #6b6e64; margin: 0; line-height: 1.4; }
      .lv-meta-row { display: flex; flex-wrap: wrap; gap: 8px 18px; margin-top: 8px; }
      .lv-meta-item { font-size: 12.5px; color: #55584f; }
      .lv-meta-item strong { color: var(--ink); }
      .lv-table-wrap { overflow-x: auto; border-radius: 8px; }
      table.lv-table { width: 100%; min-width: 700px; border-collapse: collapse; background: #fff; border-radius: 8px; overflow: hidden; border: 1.5px solid var(--paper-line); }
      .lv-table th { text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; color: #6b6e64; padding: 10px 14px; border-bottom: 1.5px solid var(--paper-line); font-weight: 700; }
      .lv-table td { padding: 12px 14px; border-bottom: 1px solid var(--paper-line); font-size: 13.5px; vertical-align: top; }
      .lv-table tr:last-child td { border-bottom: none; }
      .lv-field-name { font-weight: 700; white-space: nowrap; }
      .lv-val { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12.5px; color: #33362e; overflow-wrap: anywhere; }
      .pill { display: inline-flex; align-items: center; justify-content: center; gap: 5px; font-size: 12px; font-weight: 700; padding: 4px 9px; border-radius: 100px; white-space: nowrap; min-width: 76px; }
      .pill-match { background: #e2ede6; color: var(--green); }
      .pill-neutral { background: #e8e8e2; color: var(--neutral); }
      .pill-fail { background: #f3e0dd; color: var(--red); }
      .lv-link { display: inline-flex; align-items: center; gap: 6px; color: var(--green); font-weight: 700; text-decoration: none; }
      .lv-empty { color: #6b6e64; text-align: center; }
      .lv-spinner { animation: lv-spin 1s linear infinite; }
      .lv-source-bar { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: 22px; }
      .lv-source-toggle {
        display: inline-flex; align-items: center; justify-content: center; gap: 6px;
        border: 1.5px solid var(--paper-line); border-radius: 6px; background: #fff;
        color: var(--green); cursor: pointer; font: inherit; font-size: 13px; font-weight: 700;
        padding: 7px 11px;
      }
      .lv-doc { flex: 1 1 320px; background: #fff; border: 1.5px solid var(--paper-line); border-radius: 8px; overflow: hidden; }
      .lv-doc h3 { margin: 0; padding: 12px 14px; border-bottom: 1px solid var(--paper-line); font-size: 14px; }
      .lv-page-stack { display: grid; gap: 10px; padding: 10px; background: #f7f5ef; max-height: 620px; overflow: auto; }
      .lv-page-img { display: block; width: 100%; height: auto; border: 1px solid var(--paper-line); border-radius: 4px; background: #fff; }
      .lv-doc iframe, .lv-doc > img { display: block; width: 100%; height: 520px; border: 0; object-fit: contain; background: #fff; }
      .lv-reason { width: 100%; min-height: 86px; box-sizing: border-box; border: 1.5px solid var(--paper-line); border-radius: 8px; padding: 10px; font: inherit; }
      @keyframes lv-spin { to { transform: rotate(360deg); } }
      @media (max-width: 640px) {
        .lv-root { padding: 24px 14px; }
        .lv-toolbar, .lv-summary { align-items: flex-start; flex-direction: column; }
        .lv-form-grid { grid-template-columns: 1fr; }
        .lv-source-bar { align-items: flex-start; flex-direction: column; }
        .lv-run-btn { width: 100%; }
        table.lv-table { min-width: 620px; }
      }
    `}</style>
  );
}
