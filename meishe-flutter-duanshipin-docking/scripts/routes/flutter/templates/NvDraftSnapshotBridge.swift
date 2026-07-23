import Foundation
import UIKit
import NvShortVideoCore

@objc(NvDraftSnapshotBridge)
final class NvDraftSnapshotBridge: NSObject {
    private static let renderedMediaDirectoryName = "NvAutoCutDraftMedia"
    private static let renderedMediaDefaultsKey = "NvShortVideoRenderedDraftMedia"
    private static var captureTimer: Timer?
    private static var capturedModel: NvTimelineModel?

    @objc static func startCapture() {
        captureTimer?.invalidate()
        captureTimer = nil
        capturedModel = nil
        captureCurrentModel()

        let timer = Timer(timeInterval: 0.1, repeats: true) { _ in
            captureCurrentModel()
        }
        captureTimer = timer
        RunLoop.main.add(timer, forMode: .common)
    }

    @objc static func stopCapture() {
        captureTimer?.invalidate()
        captureTimer = nil
    }

    @objc(deleteRenderedMediaWithProjectId:)
    static func deleteRenderedMedia(projectId: String) {
        var mediaByProject = renderedMediaByProject()
        guard let mediaPath = mediaByProject.removeValue(forKey: projectId) else {
            return
        }

        do {
            if FileManager.default.fileExists(atPath: mediaPath) {
                try FileManager.default.removeItem(atPath: mediaPath)
            }
            persistRenderedMediaByProject(mediaByProject)
            print("[MeisheDraftSnapshot] deleted rendered media projectId=\(projectId) path=\(mediaPath)")
        } catch {
            print("[MeisheDraftSnapshot] rendered media cleanup failed projectId=\(projectId) error=\(error)")
        }
    }

    @objc static func stageProject(
        projectId: String,
        projectDescription: String,
        coverImagePath: String?,
        videoPath: String?
    ) -> String? {
        stopCapture()
        guard !projectId.isEmpty else {
            print("[MeisheDraftSnapshot] missing project id")
            return nil
        }

        if let sourceModel = capturedModel,
           let draftModel = sourceModel.copy() as? NvTimelineModel {
            draftModel.projectId = projectId
            if store(
                model: draftModel,
                projectId: projectId,
                projectDescription: projectDescription,
                coverImagePath: coverImagePath
            ) {
                return projectId
            }
        }

        print("[MeisheDraftSnapshot] no editable model; staging rendered video projectId=\(projectId)")
        return stageRenderedVideo(
            videoPath: videoPath,
            projectDescription: projectDescription,
            coverImagePath: coverImagePath
        )
    }

    private static func stageRenderedVideo(
        videoPath: String?,
        projectDescription: String,
        coverImagePath: String?
    ) -> String? {
        guard let rawPath = videoPath, !rawPath.isEmpty else {
            print("[MeisheDraftSnapshot] rendered video path is empty")
            return nil
        }
        let localPath: String
        if rawPath.hasPrefix("file://"), let url = URL(string: rawPath) {
            localPath = url.path
        } else {
            localPath = rawPath
        }
        guard FileManager.default.fileExists(atPath: localPath) else {
            print("[MeisheDraftSnapshot] rendered video is missing path=\(localPath)")
            return nil
        }

        guard let durableVideoURL = copyRenderedVideoToPersistentStorage(localPath: localPath) else {
            return nil
        }
        var keepDurableVideo = false
        defer {
            if !keepDurableVideo {
                try? FileManager.default.removeItem(at: durableVideoURL)
            }
        }

        if NvTimelineDataManager.managerAvailable() {
            NvTimelineDataManager.destroySharedInstance(destroyContext: false)
        }
        let manager = NvTimelineDataManager.sharedInstance()
        defer {
            NvTimelineDataManager.destroySharedInstance(destroyContext: false)
        }
        let created = manager.newProject(
            localFilePaths: [durableVideoURL.path],
            configration: NvProEditConfig()
        )
        guard created,
              let model = manager.timelineModel,
              !model.projectId.isEmpty else {
            print("[MeisheDraftSnapshot] rendered project creation failed path=\(durableVideoURL.path)")
            return nil
        }

        let draftProjectId = model.projectId
        let stored = NvProjectManager.storeCurrentProject(
            projectId: draftProjectId,
            projectDescription: projectDescription
        )
        if stored,
           let coverImagePath,
           !coverImagePath.isEmpty,
           let image = UIImage(contentsOfFile: coverImagePath) {
            _ = NvProjectManager.updateCover(image: image, projectId: draftProjectId)
        }
        let persisted = stored && NvModuleManager.projectInfoForProject(draftProjectId) != nil
        if persisted {
            var mediaByProject = renderedMediaByProject()
            mediaByProject[draftProjectId] = durableVideoURL.path
            persistRenderedMediaByProject(mediaByProject)
            keepDurableVideo = true
        }
        print("[MeisheDraftSnapshot] rendered projectId=\(draftProjectId) source=\(localPath) durableSource=\(durableVideoURL.path) created=\(created) stored=\(stored) persisted=\(persisted)")
        return persisted ? draftProjectId : nil
    }

    private static func copyRenderedVideoToPersistentStorage(localPath: String) -> URL? {
        let fileManager = FileManager.default
        guard let documentsURL = fileManager.urls(for: .documentDirectory, in: .userDomainMask).first else {
            print("[MeisheDraftSnapshot] documents directory is unavailable")
            return nil
        }

        let mediaDirectoryURL = documentsURL.appendingPathComponent(renderedMediaDirectoryName, isDirectory: true)
        let sourceURL = URL(fileURLWithPath: localPath)
        let fileExtension = sourceURL.pathExtension.isEmpty ? "mp4" : sourceURL.pathExtension
        let destinationURL = mediaDirectoryURL
            .appendingPathComponent(UUID().uuidString)
            .appendingPathExtension(fileExtension)

        do {
            try fileManager.createDirectory(at: mediaDirectoryURL, withIntermediateDirectories: true)
            try fileManager.copyItem(at: sourceURL, to: destinationURL)
            print("[MeisheDraftSnapshot] copied rendered video source=\(localPath) destination=\(destinationURL.path)")
            return destinationURL
        } catch {
            print("[MeisheDraftSnapshot] rendered video copy failed source=\(localPath) error=\(error)")
            return nil
        }
    }

    private static func renderedMediaByProject() -> [String: String] {
        UserDefaults.standard.dictionary(forKey: renderedMediaDefaultsKey) as? [String: String] ?? [:]
    }

    private static func persistRenderedMediaByProject(_ mediaByProject: [String: String]) {
        if mediaByProject.isEmpty {
            UserDefaults.standard.removeObject(forKey: renderedMediaDefaultsKey)
        } else {
            UserDefaults.standard.set(mediaByProject, forKey: renderedMediaDefaultsKey)
        }
    }

    private static func store(
        model: NvTimelineModel,
        projectId: String,
        projectDescription: String,
        coverImagePath: String?
    ) -> Bool {
        var stored = false
        NvProjectManager.storeTimelineData(model: model, sync: true, waitUntilFinished: true) { success in
            stored = success
        }
        guard stored else {
            print("[MeisheDraftSnapshot] timeline store failed projectId=\(projectId)")
            return false
        }

        _ = NvProjectManager.updateProjectInfoFile(
            projectId: projectId,
            duration: model.timelineDuration,
            projectDescription: projectDescription,
            lastModifiedTime: nil
        )
        if let coverImagePath,
           !coverImagePath.isEmpty,
           let image = UIImage(contentsOfFile: coverImagePath) {
            _ = NvProjectManager.updateCover(image: image, projectId: projectId)
        }

        let persisted = NvModuleManager.projectInfoForProject(projectId) != nil
        print("[MeisheDraftSnapshot] stored projectId=\(projectId) duration=\(model.timelineDuration) persisted=\(persisted)")
        return persisted
    }

    private static func captureCurrentModel() {
        guard NvTimelineDataManager.managerAvailable(),
              let model = NvTimelineDataManager.sharedInstance().timelineModel else {
            return
        }
        capturedModel = model
    }
}
