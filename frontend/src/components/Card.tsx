import { cn } from '../utils/cn';

interface CardProps {
  children: React.ReactNode;
  className?: string;
}

export const Card = ({ children, className }: CardProps) => {
  return (
    <div
      className={cn(
        'bg-white rounded-xl shadow-sm border border-gray-200 dark:bg-gray-800 dark:border-gray-700',
        className
      )}
    >
      {children}
    </div>
  );
};

export const CardHeader = ({ children, className }: { children: React.ReactNode; className?: string }) => {
  return (
    <div className={cn('p-6 border-b border-gray-200 dark:border-gray-700', className)}>
      {children}
    </div>
  );
};

export const CardContent = ({ children, className }: { children: React.ReactNode; className?: string }) => {
  return (
    <div className={cn('p-6', className)}>
      {children}
    </div>
  );
};

export const CardTitle = ({ children, className }: { children: React.ReactNode; className?: string }) => {
  return (
    <h3 className={cn('text-lg font-semibold text-gray-900 dark:text-gray-100', className)}>
      {children}
    </h3>
  );
};
