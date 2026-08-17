import type { ReactNode } from 'react';

interface PageHeaderProps {
  description?: ReactNode;
  eyebrow?: string;
  meta?: ReactNode;
  status?: ReactNode;
  title: string;
}

export function PageHeader({ description, eyebrow, meta, status, title }: PageHeaderProps) {
  return (
    <header className="page-header">
      <div className="page-header__main">
        {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
        <div className="page-header__title-row">
          <h1>{title}</h1>
          {status}
        </div>
        {description ? <p className="page-header__description">{description}</p> : null}
      </div>
      {meta ? <div className="page-header__meta">{meta}</div> : null}
    </header>
  );
}
