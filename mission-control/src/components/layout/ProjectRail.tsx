/**
 * ProjectRail - Left sidebar showing project list with health indicators
 * 
 * This component displays all projects with their breathing health dots
 * and unread counts. It's the left column of the Mission Control layout.
 * 
 * Features:
 * - Breathing health dots that pulse based on project status
 * - Unread count badges
 * - Collapsible rail for more space
 * - Liquid glass morphing effects
 * - Project filtering
 * 
 * Why this component exists:
 * - Provides quick access to all projects
 * - Shows health status at a glance
 * - Enables project-based filtering of the feed
 * - Maintains context while working on specific projects
 * 
 * For AI agents: This is the project navigation component.
 * Projects are displayed with health indicators and unread counts.
 */

import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { clsx } from 'clsx'
import { LiquidCard } from '@/components/core/LiquidCard'
import { HealthDot } from '@/components/core/HealthDot'
import { tokens } from '@/styles/tokens'
import type { ProjectSummary } from '@/types'

interface ProjectRailProps {
  projects: ProjectSummary[]
  selectedProject: string | null
  onProjectSelect: (projectId: string | null) => void
  loading: boolean
  error: string | null
  collapsed: boolean
  onToggleCollapse: () => void
  isMobile: boolean
}

export const ProjectRail: React.FC<ProjectRailProps> = ({
  projects,
  selectedProject,
  onProjectSelect,
  loading,
  error,
  collapsed,
  onToggleCollapse,
  isMobile,
}) => {
  const [searchQuery, setSearchQuery] = useState('')
  const [hoveredProject, setHoveredProject] = useState<string | null>(null)

  // Filter projects based on search query
  const filteredProjects = projects.filter(project =>
    project.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    project.description?.toLowerCase().includes(searchQuery.toLowerCase())
  )

  // Handle project selection
  const handleProjectSelect = (projectId: string) => {
    if (selectedProject === projectId) {
      onProjectSelect(null) // Deselect if already selected
    } else {
      onProjectSelect(projectId)
    }
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-white/10">
        {!collapsed && !isMobile && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-center space-x-2"
          >
            <h2 className="text-lg font-semibold text-white">Projects</h2>
            <div className="text-xs text-white/60 bg-white/10 px-2 py-1 rounded-full">
              {projects.length}
            </div>
          </motion.div>
        )}

        {/* Collapse toggle */}
        <motion.button
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          onClick={onToggleCollapse}
          className="p-2 rounded-lg bg-white/10 hover:bg-white/20 transition-colors"
          aria-label={collapsed ? 'Expand projects' : 'Collapse projects'}
        >
          <svg
            className={clsx(
              'w-4 h-4 transition-transform',
              collapsed ? 'rotate-0' : 'rotate-180'
            )}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </motion.button>
      </div>

      {/* Search bar */}
      <AnimatePresence>
        {!collapsed && !isMobile && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="p-4 border-b border-white/10"
          >
            <div className="relative">
              <input
                type="text"
                placeholder="Search projects..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full px-3 py-2 pl-9 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/50 focus:outline-none focus:border-white/20 focus:bg-white/10 transition-all"
              />
              <svg
                className="absolute left-3 top-2.5 w-4 h-4 text-white/50"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Projects list */}
      <div className="flex-1 overflow-y-auto p-2">
        {loading && (
          <div className="space-y-2">
            {[...Array(5)].map((_, i) => (
              <div
                key={i}
                className="h-16 bg-white/5 rounded-lg animate-pulse"
              />
            ))}
          </div>
        )}

        {error && (
          <div className="p-4 text-center">
            <div className="text-red-400 text-sm mb-2">Failed to load projects</div>
            <button
              onClick={() => window.location.reload()}
              className="text-xs text-white/60 hover:text-white/80"
            >
              Try again
            </button>
          </div>
        )}

        {!loading && !error && (
          <AnimatePresence>
            <div className="space-y-2">
              {filteredProjects.map((project, index) => (
                <ProjectCard
                  key={project.id}
                  project={project}
                  isSelected={selectedProject === project.id}
                  isHovered={hoveredProject === project.id}
                  collapsed={collapsed}
                  onSelect={() => handleProjectSelect(project.id)}
                  onHover={setHoveredProject}
                  index={index}
                />
              ))}
            </div>
          </AnimatePresence>
        )}

        {!loading && !error && filteredProjects.length === 0 && (
          <div className="p-4 text-center text-white/60">
            <div className="text-sm">No projects found</div>
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="text-xs text-white/40 hover:text-white/60 mt-1"
              >
                Clear search
              </button>
            )}
          </div>
        )}
      </div>

      {/* Add project button */}
      <AnimatePresence>
        {!collapsed && !isMobile && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            className="p-4 border-t border-white/10"
          >
            <button className="w-full p-3 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-white/70 hover:text-white transition-all flex items-center justify-center space-x-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              <span className="text-sm">Add Project</span>
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

interface ProjectCardProps {
  project: ProjectSummary
  isSelected: boolean
  isHovered: boolean
  collapsed: boolean
  onSelect: () => void
  onHover: (projectId: string | null) => void
  index: number
}

const ProjectCard: React.FC<ProjectCardProps> = ({
  project,
  isSelected,
  isHovered,
  collapsed,
  onSelect,
  onHover,
  index,
}) => {
  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.05 }}
      onMouseEnter={() => onHover(project.id)}
      onMouseLeave={() => onHover(null)}
    >
      <LiquidCard
        variant="project"
        severity={project.health === 'red' ? 'red' : project.health === 'amber' ? 'amber' : 'info'}
        urgency={project.health === 'red' ? 'high' : project.health === 'amber' ? 'medium' : 'low'}
        onClick={onSelect}
        className={clsx(
          'transition-all duration-300',
          isSelected && 'ring-2 ring-green-500/50',
          collapsed ? 'p-2' : 'p-3'
        )}
        breathingAnimation={project.health !== 'green'}
      >
        <div className="flex items-center space-x-3">
          {/* Health indicator */}
          <div className="flex-shrink-0">
            <HealthDot
              health={project.health}
              size="md"
              showGlow={isSelected || isHovered}
              showPulse={project.health !== 'green'}
              interactive={true}
              aria-label={`${project.name} health: ${project.health}`}
            />
          </div>

          {/* Project info */}
          <AnimatePresence>
            {!collapsed && (
              <motion.div
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: 'auto' }}
                exit={{ opacity: 0, width: 0 }}
                className="flex-1 min-w-0"
              >
                <div className="flex items-center justify-between">
                  <h3 className="font-medium text-white truncate text-sm">
                    {project.name}
                  </h3>
                  
                  {/* Unread count */}
                  {project.unreadCount > 0 && (
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      className="flex-shrink-0 ml-2"
                    >
                      <div className="bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                        {project.unreadCount > 99 ? '99+' : project.unreadCount}
                      </div>
                    </motion.div>
                  )}
                </div>

                {/* Description */}
                {project.description && (
                  <p className="text-xs text-white/60 truncate mt-1">
                    {project.description}
                  </p>
                )}

                {/* Last activity */}
                <div className="text-xs text-white/40 mt-1">
                  {new Date(project.lastActivity).toLocaleDateString()}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </LiquidCard>
    </motion.div>
  )
}

export default ProjectRail