#include "InterframePluginModule.h"
#include "SInterframeReviewTab.h"
#include "Widgets/Docking/SDockTab.h"
#include "Framework/Docking/TabManager.h"

static const FName InterframeTabName("InterframeContinuityReview");

#define LOCTEXT_NAMESPACE "FInterframePluginModule"

void FInterframePluginModule::StartupModule()
{
    FGlobalTabmanager::Get()->RegisterNomadTabSpawner(
        InterframeTabName,
        FOnSpawnTab::CreateRaw(this, &FInterframePluginModule::OnSpawnPluginTab))
        .SetDisplayName(LOCTEXT("FInterframeTabTitle", "Interframe Continuity QA"))
        .SetMenuType(ETabSpawnerMenuType::Hidden);
}

void FInterframePluginModule::ShutdownModule()
{
    FGlobalTabmanager::Get()->UnregisterNomadTabSpawner(InterframeTabName);
}

TSharedRef<SDockTab> FInterframePluginModule::OnSpawnPluginTab(const FSpawnTabArgs& SpawnTabArgs)
{
    return SNew(SDockTab)
        .TabRole(ETabRole::NomadTab)
        [
            SNew(SInterframeReviewTab)
        ];
}

#undef LOCTEXT_NAMESPACE

IMPLEMENT_MODULE(FInterframePluginModule, InterframePlugin)
