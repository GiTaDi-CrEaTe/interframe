#pragma once

#include "CoreMinimal.h"
#include "EditorValidatorBase.h"
#include "InterframeEditorValidator.generated.h"

/**
 * Integrates Interframe deterministic continuity checks (IF-001..IF-004, IF-007, IF-008)
 * directly into Unreal Engine's Data Validation subsystem (Blueprint Section 4 & Section 5).
 */
UCLASS()
class INTERFRAMEPLUGIN_API UInterframeEditorValidator : public UEditorValidatorBase
{
    GENERATED_BODY()

public:
    UInterframeEditorValidator();

protected:
    virtual bool CanValidateAsset_Implementation(
        const FAssetData& InAssetData,
        UObject* InObject,
        FDataValidationContext& InContext) const override;

    virtual EDataValidationResult ValidateLoadedAsset_Implementation(
        const FAssetData& InAssetData,
        UObject* InAsset,
        FDataValidationContext& Context) override;
};
