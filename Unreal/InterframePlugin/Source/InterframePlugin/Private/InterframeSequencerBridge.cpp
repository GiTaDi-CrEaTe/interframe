#include "InterframeSequencerBridge.h"
#include "LevelSequence.h"
#include "MovieScene.h"
#include "Tracks/MovieSceneCameraCutTrack.h"
#include "Sections/MovieSceneCameraCutSection.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/SecureHash.h"
#include "HAL/PlatformProcess.h"
#include "Serialization/JsonWriter.h"
#include "Serialization/JsonSerializer.h"

bool FInterframeSequencerBridge::ExtractSequenceManifest(
    const ULevelSequence* InSequence,
    const FString& InRenderProfileId,
    TArray<FInterframeShotManifest>& OutShots,
    FString& OutManifestJson)
{
    if (!InSequence || !InSequence->GetMovieScene())
    {
        return false;
    }

    const UMovieScene* MovieScene = InSequence->GetMovieScene();
    const FFrameRate TickResolution = MovieScene->GetTickResolution();
    const FFrameRate DisplayRate = MovieScene->GetDisplayRate();

    FAssetRegistryModule& AssetRegistryModule =
        FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");

    OutShots.Reset();

    const UMovieSceneTrack* CameraCutTrack = MovieScene->GetCameraCutTrack();
    if (CameraCutTrack)
    {
        int32 ShotIdx = 1;
        for (UMovieSceneSection* Section : CameraCutTrack->GetAllSections())
        {
            const UMovieSceneCameraCutSection* CutSection = Cast<UMovieSceneCameraCutSection>(Section);
            if (!CutSection)
            {
                continue;
            }

            FInterframeShotManifest Shot;
            Shot.ShotId = FString::Printf(TEXT("SH_%03d"), ShotIdx++);
            const TRange<FFrameNumber> Range = CutSection->GetRange();
            if (Range.GetLowerBound().IsClosed() && Range.GetUpperBound().IsClosed())
            {
                Shot.StartFrame = FFrameRate::TransformTime(
                    Range.GetLowerBoundValue(), TickResolution, DisplayRate).FloorToFrame().Value;
                Shot.EndFrame = FFrameRate::TransformTime(
                    Range.GetUpperBoundValue(), TickResolution, DisplayRate).FloorToFrame().Value;
            }
            Shot.FrameRate = DisplayRate.AsDecimal();
            Shot.CameraGuid = CutSection->GetCameraBindingID().GetGuid().ToString(EGuidFormats::DigitsWithHyphensLower);

            for (const FMovieSceneBinding& Binding : MovieScene->GetBindings())
            {
                FInterframeActorBindingManifest ActorManifest;
                ActorManifest.ActorGuid = Binding.GetObjectGuid().ToString(EGuidFormats::DigitsWithHyphensLower);
                ActorManifest.ActorLabel = Binding.GetName();
                ActorManifest.bBoundInSequencer = true;
                ActorManifest.bVisibilityState = true;
                Shot.ActorBindings.Add(ActorManifest);
            }

            OutShots.Add(Shot);
        }
    }

    TSharedRef<FJsonObject> RootObj = MakeShared<FJsonObject>();
    RootObj->SetStringField(TEXT("schema_version"), TEXT("1.0.0"));
    RootObj->SetStringField(TEXT("project_id_hash"), FMD5::HashAnsiString(*FPaths::GetProjectFilePath()).Left(16));
    RootObj->SetStringField(TEXT("engine_version"), TEXT("5.8.0"));
    RootObj->SetStringField(TEXT("sequence_id"), InSequence->GetName());
    RootObj->SetStringField(TEXT("sequence_path"), InSequence->GetPathName());
    RootObj->SetStringField(TEXT("render_profile_id"), InRenderProfileId);
    RootObj->SetStringField(TEXT("collector_version"), TEXT("1.0.0-ue5.8"));

    TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&OutManifestJson);
    FJsonSerializer::Serialize(RootObj, Writer);
    return true;
}

bool FInterframeSequencerBridge::RunContinuityCheckOnSequence(
    const ULevelSequence* InSequence,
    const FString& InValidationProfile,
    TArray<FInterframeIssueRecord>& OutIssues,
    FString& OutReportPath)
{
    TArray<FInterframeShotManifest> Shots;
    FString ManifestJson;
    if (!ExtractSequenceManifest(InSequence, InValidationProfile, Shots, ManifestJson))
    {
        return false;
    }

    const FString ManifestDir = FPaths::ProjectSavedDir() / TEXT("Interframe/Manifests");
    const FString ReportDir = FPaths::ProjectSavedDir() / TEXT("Interframe/Reports");
    IFileManager::Get().MakeDirectory(*ManifestDir, true);
    IFileManager::Get().MakeDirectory(*ReportDir, true);

    const FString ManifestPath = ManifestDir / (InSequence->GetName() + TEXT(".manifest.v1.json"));
    OutReportPath = ReportDir / (InSequence->GetName() + TEXT(".issues.v1.json"));

    if (!FFileHelper::SaveStringToFile(ManifestJson, *ManifestPath))
    {
        return false;
    }

    const FString PythonScriptPath = FPaths::ProjectPluginsDir() /
        TEXT("InterframePlugin/../../python/interframe_engine/cli.py");
    const FString Args = FString::Printf(
        TEXT(""%s" analyze --manifest "%s" --out "%s""),
        *PythonScriptPath, *ManifestPath, *OutReportPath);

    int32 ReturnCode = 0;
    FString StdOut;
    FString StdErr;
    FPlatformProcess::ExecProcess(TEXT("python3"), *Args, &ReturnCode, &StdOut, &StdErr);
    return (ReturnCode == 0);
}

bool FInterframeSequencerBridge::RecordReviewerDisposition(
    const FString& InIssueId,
    EInterframeReviewerDecision InDecision,
    const FString& InReviewerNotes)
{
    return !InIssueId.IsEmpty();
}
