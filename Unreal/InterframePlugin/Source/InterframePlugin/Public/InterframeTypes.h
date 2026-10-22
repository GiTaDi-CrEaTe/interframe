#pragma once

#include "CoreMinimal.h"
#include "InterframeTypes.generated.h"

UENUM(BlueprintType)
enum class EInterframeSeverity : uint8
{
    Critical UMETA(DisplayName = "Critical"),
    Major UMETA(DisplayName = "Major"),
    Minor UMETA(DisplayName = "Minor"),
    Informational UMETA(DisplayName = "Informational")
};

UENUM(BlueprintType)
enum class EInterframeReviewerDecision : uint8
{
    Unresolved UMETA(DisplayName = "Unresolved"),
    TruePositive UMETA(DisplayName = "True Positive"),
    FalsePositive UMETA(DisplayName = "False Positive"),
    IntentionalChange UMETA(DisplayName = "Intentional Change")
};

USTRUCT(BlueprintType)
struct FInterframeTransformSample
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interframe")
    int32 Frame = 0;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interframe")
    double TimeSeconds = 0.0;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interframe")
    FVector LocationCm = FVector::ZeroVector;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interframe")
    FRotator RotationDeg = FRotator::ZeroRotator;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interframe")
    FVector Scale = FVector::OneVector;
};

USTRUCT(BlueprintType)
struct FInterframeActorBindingManifest
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interframe")
    FString ActorGuid;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interframe")
    FString ActorLabel;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interframe")
    FString AssetPath;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interframe")
    bool bAssetExistsInRegistry = true;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interframe")
    bool bBoundInSequencer = true;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interframe")
    bool bVisibilityState = true;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interframe")
    FString MeshId;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interframe")
    TArray<FString> MaterialIds;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interframe")
    int32 StencilObjectId = 0;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interframe")
    TArray<FInterframeTransformSample> TransformSamples;
};

USTRUCT(BlueprintType)
struct FInterframeShotManifest
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interframe")
    FString ShotId;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interframe")
    int32 StartFrame = 0;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interframe")
    int32 EndFrame = 0;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interframe")
    double FrameRate = 24.0;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interframe")
    FString ContinuityAnchor = TEXT("continuous_action");

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interframe")
    FString CameraGuid;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interframe")
    FString CameraName;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interframe")
    float FocalLengthMm = 35.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interframe")
    TArray<FInterframeActorBindingManifest> ActorBindings;
};

USTRUCT(BlueprintType)
struct FInterframeIssueRecord
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interframe")
    FString IssueId;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interframe")
    FString RuleId;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interframe")
    FString IssueType;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interframe")
    EInterframeSeverity Severity = EInterframeSeverity::Major;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interframe")
    float Confidence = 1.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interframe")
    FString SequencePath;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interframe")
    FString ShotId;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interframe")
    int32 Frame = 0;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interframe")
    FString ActorGuid;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interframe")
    FString AssetPath;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interframe")
    FString OneSentenceExplanation;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interframe")
    FString EvidenceUri;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interframe")
    EInterframeReviewerDecision ReviewerDecision = EInterframeReviewerDecision::Unresolved;
};
