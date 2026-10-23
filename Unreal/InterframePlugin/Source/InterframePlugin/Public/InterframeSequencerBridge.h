#pragma once

#include "CoreMinimal.h"
#include "InterframeTypes.h"

class ULevelSequence;

/**
 * Bridges Unreal Engine Sequencer, Asset Registry, and Movie Render Queue
 * to the local Interframe continuity diagnostic pipeline.
 */
class INTERFRAMEPLUGIN_API FInterframeSequencerBridge
{
public:
    /** Extracts a reproducible shot manifest from a ULevelSequence asset. */
    static bool ExtractSequenceManifest(
        const ULevelSequence* InSequence,
        const FString& InRenderProfileId,
        TArray<FInterframeShotManifest>& OutShots,
        FString& OutManifestJson);

    /** Writes a manifest to Saved/Interframe/Manifests/ and invokes the local worker. */
    static bool RunContinuityCheckOnSequence(
        const ULevelSequence* InSequence,
        const FString& InValidationProfile,
        TArray<FInterframeIssueRecord>& OutIssues,
        FString& OutReportPath);

    /** Persists a reviewer's decision (True Positive, False Positive, Intentional Change). */
    static bool RecordReviewerDisposition(
        const FString& InIssueId,
        EInterframeReviewerDecision InDecision,
        const FString& InReviewerNotes);
};
