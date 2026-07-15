import { Loader2, Trash2 } from "lucide-react";

import type { BookSummary } from "../types";

type DeleteBookDialogProps = {
  book: BookSummary;
  deletingBookId: string | null;
  onCancel: () => void;
  onConfirm: () => void;
};

export function DeleteBookDialog({
  book,
  deletingBookId,
  onCancel,
  onConfirm
}: DeleteBookDialogProps) {
  const isDeleting = deletingBookId === book.id;
  return (
    <div className="modal-backdrop" role="presentation">
      <section
        aria-labelledby="delete-book-title"
        aria-modal="true"
        className="confirm-dialog"
        role="dialog"
      >
        <div>
          <p className="eyebrow">删除书籍</p>
          <h2 id="delete-book-title">确定删除《{book.title}》？</h2>
        </div>
        <p className="confirm-copy">
          删除后会清理这本书的正文、上传源文件、已生成音频和本地阅读状态。这个操作不能撤销。
        </p>
        <div className="confirm-actions">
          <button className="ghost-button" disabled={isDeleting} onClick={onCancel} type="button">
            取消
          </button>
          <button className="danger-button" disabled={isDeleting} onClick={onConfirm} type="button">
            {isDeleting ? <Loader2 className="spin" size={16} /> : <Trash2 size={16} />}
            <span>确认删除</span>
          </button>
        </div>
      </section>
    </div>
  );
}
