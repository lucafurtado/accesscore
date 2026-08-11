import { ChevronLeft, ChevronRight } from "lucide-react";

import { Button } from "@/components/ui/button";

interface CursorPaginationProps {
  onPrevious: () => void;
  onNext: () => void;
  canGoPrevious: boolean;
  canGoNext: boolean;
}

export function CursorPagination({
  onPrevious,
  onNext,
  canGoPrevious,
  canGoNext,
}: CursorPaginationProps) {
  return (
    <div className="flex items-center justify-end gap-2 pt-4">
      <Button variant="outline" size="sm" onClick={onPrevious} disabled={!canGoPrevious}>
        <ChevronLeft className="mr-1 h-4 w-4" />
        Previous
      </Button>
      <Button variant="outline" size="sm" onClick={onNext} disabled={!canGoNext}>
        Next
        <ChevronRight className="ml-1 h-4 w-4" />
      </Button>
    </div>
  );
}
