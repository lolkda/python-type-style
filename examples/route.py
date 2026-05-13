"""FastAPI 路由示例,展示可复用 Annotated 别名 + BaseResponse[T] 的标准外向契约。"""

from typing import Annotated

from fastapi import APIRouter, Path, Query

from _shared import BaseResponse, PageData, UserDetailData


type UserId = Annotated[int, Path(gt=0, description="用户唯一标识")]
type PageNum = Annotated[int, Query(ge=1, description="页码,从 1 开始")]
type PageSize = Annotated[int, Query(ge=1, le=100, description="每页大小,上限 100")]


router = APIRouter()


@router.api_route(
    path="/users/{user_id}",
    methods=["GET"],
    response_model=BaseResponse[UserDetailData],
    tags=["用户中心"],
    summary="查询用户详情",
)
async def get_user_detail(*, user_id: UserId) -> BaseResponse[UserDetailData]:
    """
    用途:
        按用户标识查询详情信息并返回统一外壳包装的数据。

    Args:
        user_id: 路径参数,目标用户唯一标识。

    Returns:
        BaseResponse[UserDetailData]: 统一外壳包装的用户详情数据。
    """
    data = UserDetailData(user_id=user_id, nickname="示例用户", avatar_url=None)
    return BaseResponse.ok(data)


@router.api_route(
    path="/users",
    methods=["GET"],
    response_model=BaseResponse[PageData[UserDetailData]],
    tags=["用户中心"],
    summary="分页查询用户列表",
)
async def list_users(
    *,
    page: PageNum = 1,
    size: PageSize = 20,
) -> BaseResponse[PageData[UserDetailData]]:
    """
    用途:
        分页查询用户列表并返回统一外壳包装的分页载荷。

    Args:
        page: 查询参数,页码从 1 开始。
        size: 查询参数,每页大小,上限 100。

    Returns:
        BaseResponse[PageData[UserDetailData]]: 统一外壳包装的分页数据。
    """
    items: list[UserDetailData] = []
    total = 0
    return BaseResponse.ok(PageData(items=items, total=total, page=page, size=size))


__all__ = [
    "PageNum",
    "PageSize",
    "UserId",
    "get_user_detail",
    "list_users",
    "router",
]
