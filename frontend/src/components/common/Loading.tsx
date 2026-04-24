interface LoadingProps {
  text?: string;
  progress?: number;
}

export function Loading({ text = '处理中...', progress }: LoadingProps) {
  return (
    <div className="flex flex-col items-center justify-center p-8">
      <div className="w-16 h-16 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
      <p className="mt-4 text-gray-600">{text}</p>
      {progress !== undefined && (
        <div className="w-full max-w-md mt-4">
          <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-600 transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-sm text-gray-500 text-center mt-2">{progress}%</p>
        </div>
      )}
    </div>
  );
}
