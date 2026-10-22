using UnrealBuildTool;

public class InterframePlugin : ModuleRules
{
    public InterframePlugin(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = ModuleRules.PCHUsageMode.UseExplicitOrSharedPCHs;

        PublicDependencyModuleNames.AddRange(
            new string[]
            {
                "Core",
                "CoreUObject",
                "Engine",
                "LevelSequence",
                "MovieScene",
                "MovieSceneTracks",
                "MovieRenderPipelineCore",
                "DataValidation"
            }
        );

        PrivateDependencyModuleNames.AddRange(
            new string[]
            {
                "UnrealEd",
                "Slate",
                "SlateCore",
                "EditorStyle",
                "WorkspaceMenuStructure",
                "LevelSequenceEditor",
                "Sequencer",
                "AssetRegistry",
                "Json",
                "JsonUtilities",
                "Projects",
                "ToolMenus"
            }
        );
    }
}
