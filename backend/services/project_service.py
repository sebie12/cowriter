from sqlalchemy.exc import IntegrityError

if __package__ and __package__.startswith("backend."):
    from ..database import Project, db
else:
    from database import Project, db


class ProjectService:
    def get_project_by_id(self, project_id):
        return db.session.get(Project, project_id)

    def create_project(self, project):
        db.session.add(project)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise
        return project

    def update_project(self, project_id, name=None, description=None):
        project = self.get_project_by_id(project_id)
        if project:
            if name is not None:
                project.name = name
            if description is not None:
                project.description = description
            db.session.commit()
        return project

    def delete_project(self, project_id):
        project = self.get_project_by_id(project_id)
        if project:
            db.session.delete(project)
            db.session.commit()
        return project

    def get_all_projects(self):
        return Project.query.order_by(Project.updated_at.desc(), Project.id.desc()).all()

    def get_current_project(self):
        return Project.query.order_by(Project.opened_at.desc(), Project.id.desc()).first()

    def project_opened(self, project_id):
        project = self.get_project_by_id(project_id)
        if project:
            project.opened_at = db.func.now()
            db.session.commit()
        return project