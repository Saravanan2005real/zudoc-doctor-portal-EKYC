def require_role(*allowed_roles):
    def middleware(request, next_handler):
        role_val = request.context.get("admin_role")
        if not role_val:
            role_header = request.headers.get("X-Admin-Role")
            if role_header:
                role_val = role_header
                
        if not role_val:
            return {"error": "Unauthorized: Admin authentication token required"}, 401
            
        authorized = False
        for role in allowed_roles:
            if role_val == role or role_val == "SUPER_ADMIN":
                authorized = True
                break
                
        if not authorized:
            return {"error": "Forbidden: Insufficient administrative privileges to perform this action"}, 403
            
        return next_handler(request)
    return middleware

def with_admin_context(context, admin_id, role):
    context["admin_id"] = admin_id
    context["admin_role"] = role
    return context
