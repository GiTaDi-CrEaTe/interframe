#include "InterframeEditorValidator.h"
#include "InterframeSequencerBridge.h"
#include "LevelSequence.h"
#include "Misc/DataValidation.h"

UInterframeEditorValidator::UInterframeEditorValidator()
    : Super()
{
    bIsEnabled = true;
}

bool UInterframeEditorValidator::CanValidateAsset_Implementation(
    const FAssetData& InAssetData,
    UObject* InObject,
    FDataValidationContext& InContext) const
{
    return InObject && InObject->IsA<ULevelSequence>();
}

EDataValidationResult UInterframeEditorValidator::ValidateLoadedAsset_Implementation(
    const FAssetData& InAssetData,
    UObject* InAsset,
    FDataValidationContext& Context)
{
    const ULevelSequence* Sequence = Cast<ULevelSequence>(InAsset);
    if (!Sequence)
    {
        return EDataValidationResult::NotValidated;
    }

    TArray<FInterframeIssueRecord> Issues;
    FString ReportPath;
    if (!FInterframeSequencerBridge::RunContinuityCheckOnSequence(
            Sequence, TEXT("DefaultDeterministicProfile"), Issues, ReportPath))
    {
        AssetWarning(InAsset, FText::FromString(TEXT("Interframe failed to extract LevelSequence manifest.")));
        return EDataValidationResult::Valid;
    }

    bool bHasCriticalFailure = false;
    for (const FInterframeIssueRecord& Issue : Issues)
    {
        const FText Message = FText::FromString(FString::Printf(
            TEXT("[%s | %s | Frame %d] %s (Confidence: %.2f)"),
            *Issue.RuleId, *Issue.ShotId, Issue.Frame, *Issue.OneSentenceExplanation, Issue.Confidence));

        if (Issue.Severity == EInterframeSeverity::Critical)
        {
            AssetFails(InAsset, Message);
            bHasCriticalFailure = true;
        }
        else
        {
            AssetWarning(InAsset, Message);
        }
    }

    if (!bHasCriticalFailure)
    {
        AssetPasses(InAsset);
        return EDataValidationResult::Valid;
    }
    return EDataValidationResult::Invalid;
}
