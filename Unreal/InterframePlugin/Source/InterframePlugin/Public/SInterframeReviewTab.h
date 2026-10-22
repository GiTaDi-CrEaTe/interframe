#pragma once

#include "CoreMinimal.h"
#include "Widgets/SCompoundWidget.h"
#include "InterframeTypes.h"

/**
 * Dockable Unreal Editor Slate tab for selecting Level Sequences, running hybrid
 * continuity diagnostics, viewing shot-level evidence, and recording artist decisions.
 */
class SInterframeReviewTab : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SInterframeReviewTab) {}
    SLATE_END_ARGS()

    void Construct(const FArguments& InArgs);

private:
    FReply OnRunDiagnosticsClicked();
    FReply OnExportHtmlReportClicked();

    TArray<TSharedPtr<FInterframeIssueRecord>> CachedIssues;
};
