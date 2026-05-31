type Props = {
  page: number;
  pages: number;
  total: number;
  pageSize: number;
  onPageChange: (page: number) => void;
};

export default function JobPagination({ page, pages, total, pageSize, onPageChange }: Props) {
  if (total === 0) return null;

  const from = (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);

  return (
    <div className="job-pagination">
      <span className="job-pagination__info">
        {from}–{to} of {total}
      </span>
      <div className="job-pagination__controls">
        <button
          type="button"
          className="btn btn-ghost"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
        >
          Previous
        </button>
        <span className="job-pagination__page">
          Page {page} / {pages}
        </span>
        <button
          type="button"
          className="btn btn-ghost"
          disabled={page >= pages}
          onClick={() => onPageChange(page + 1)}
        >
          Next
        </button>
      </div>
    </div>
  );
}
