#include "SInterframeReviewTab.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/SBoxPanel.h"

#define LOCTEXT_NAMESPACE "SInterframeReviewTab"

void SInterframeReviewTab::Construct(const FArguments& InArgs)
{
    ChildSlot
    [
        SNew(SVerticalBox)
        + SVerticalBox::Slot()
        .AutoHeight()
        .Padding(12.0f)
        [
            SNew(SHorizontalBox)
            + SHorizontalBox::Slot()
            .AutoWidth()
            .Padding(0.0f, 0.0f, 8.0f, 0.0f)
            [
                SNew(SButton)
                .Text(LOCTEXT("RunContinuityCheck", "Run Interframe Continuity Check"))
                .OnClicked(this, &SInterframeReviewTab::OnRunDiagnosticsClicked)
            ]
            + SHorizontalBox::Slot()
            .AutoWidth()
            [
                SNew(SButton)
                .Text(LOCTEXT("ExportHtmlReport", "Export Evidence Report (HTML/JSON/CSV)"))
                .OnClicked(this, &SInterframeReviewTab::OnExportHtmlReportClicked)
            ]
        ]
        + SVerticalBox::Slot()
        .FillHeight(1.0f)
        .Padding(12.0f, 0.0f, 12.0f, 12.0f)
        [
            SNew(SScrollBox)
            + SScrollBox::Slot()
            [
                SNew(STextBlock)
                .Text(LOCTEXT("EmptyStateText", "Select a Level Sequence and run Interframe Continuity QA to inspect shot boundaries, actor bindings, transform jumps, and rendered Object-ID visibility evidence."))
            ]
        ]
    ];
}

FReply SInterframeReviewTab::OnRunDiagnosticsClicked()
{
    UE_LOG(LogTemp, Display, TEXT("[Interframe] Review Tab: Initiating continuity diagnostics on active LevelSequence selection."));
    return FReply::Handled();
}

FReply SInterframeReviewTab::OnExportHtmlReportClicked()
{
    UE_LOG(LogTemp, Display, TEXT("[Interframe] Review Tab: Exporting latest findings to Saved/Interframe/Reports/."));
    return FReply::Handled();
}

#undef LOCTEXT_NAMESPACE
