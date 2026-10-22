#pragma once

#include "CoreMinimal.h"
#include "Modules/ModuleManager.h"

class FInterframePluginModule : public IModuleInterface
{
public:
    virtual void StartupModule() override;
    virtual void ShutdownModule() override;

private:
    TSharedRef<class SDockTab> OnSpawnPluginTab(const class FSpawnTabArgs& SpawnTabArgs);
};
